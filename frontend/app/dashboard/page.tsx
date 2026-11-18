"use client";

import { useEffect, useState } from "react";
import ContentSubmissionForm from "@/components/content-submission-form";
import OutputTypeSelector from "@/components/output-type-selector";
import GenerationControls from "@/components/generation-controls";
import OutputPreviewCard from "@/components/output-preview-card";
import PublishModal from "@/components/publish-modal";
import AccountManager from "@/components/account-manager";
import { Button } from "@/components/ui/button";
import {
  listOutputTypes,
  generateOutputs,
  generateFromMedia,
  listConnectedAccounts,
  completeOAuthCallback,
  type GenerationParams,
  type ConnectedAccount,
} from "@/lib/api-client";
import { OUTPUT_TYPE_LABELS } from "@/lib/constants";
import { Shield, Sparkles, CheckCircle2 } from "lucide-react";

interface OutputResult {
  status: "done" | "failed";
  data?: Record<string, unknown>;
  error?: string;
}

export default function Dashboard() {
  const [sourceContent, setSourceContent] = useState("");
  const [mediaFile, setMediaFile] = useState<File | null>(null);
  // The supported types are part of the dashboard contract, so render them
  // immediately instead of leaving this panel empty during backend startup.
  const [availableTypes, setAvailableTypes] = useState<string[]>(() => Object.keys(OUTPUT_TYPE_LABELS));
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [params, setParams] = useState<GenerationParams>({});
  const [results, setResults] = useState<Record<string, OutputResult | { status: "generating" }>>({});
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Accounts & Publishing states
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [isAccountManagerOpen, setIsAccountManagerOpen] = useState(false);
  const [activePublish, setActivePublish] = useState<{
    outputType: string;
    data: Record<string, unknown>;
  } | null>(null);
  const [bannerNotice, setBannerNotice] = useState<string | null>(null);

  async function refreshAccounts() {
    try {
      const list = await listConnectedAccounts();
      setAccounts(list);
    } catch {
      // Backend may be unavailable during initial spinup
    }
  }

  // Load available deliverables and connected accounts
  useEffect(() => {
    listOutputTypes()
      .then((types) => {
        if (types.length > 0) setAvailableTypes(types);
      })
      .catch(() => {
        // Keep the built-in options visible. Generation will still provide a
        // clear error if the backend has not finished starting.
      });

    refreshAccounts();

    // Check for incoming OAuth callback in URL
    if (typeof window !== "undefined") {
      const searchParams = new URLSearchParams(window.location.search);
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const platformParam = searchParams.get("oauth") || searchParams.get("platform");
      const connectedPlatform = searchParams.get("connected");
      const oauthError = searchParams.get("oauth_error");

      if (connectedPlatform) {
        setBannerNotice(`Successfully connected ${connectedPlatform === "gmail" ? "Gmail" : "LinkedIn"} account!`);
        refreshAccounts();
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
      }

      if (oauthError) {
        setError(`OAuth connection failed: ${oauthError}`);
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
      }

      if (code && state && platformParam) {
        const platform = platformParam.toLowerCase() === "gmail" ? "gmail" : "linkedin";

        completeOAuthCallback(platform, code, state)
          .then((res) => {
            setBannerNotice(
              `Successfully connected ${
                res.account?.platform === "linkedin" ? "LinkedIn"
                : "Gmail"
              } account (${res.account?.account_name})!`
            );
            refreshAccounts();
          })
          .catch((err) => {
            setError(`OAuth connection failed: ${err.message}`);
          })
          .finally(() => {
            // Clean browser URL query string
            window.history.replaceState({}, document.title, window.location.pathname);
          });
      }
    }
  }, []);

  async function handleGenerate() {
    const usingMedia = !!mediaFile;
    if ((!usingMedia && !sourceContent.trim()) || selectedTypes.length === 0) return;

    setError(null);
    setGenerating(true);
    setResults(Object.fromEntries(selectedTypes.map((t) => [t, { status: "generating" as const }])));

    try {
      const response = usingMedia
        ? await generateFromMedia(mediaFile!, selectedTypes, params)
        : await generateOutputs({ source_content: sourceContent, output_types: selectedTypes, params });
      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  const hasSource = mediaFile !== null || sourceContent.trim().length > 0;
  const canGenerate = hasSource && selectedTypes.length > 0 && !generating;

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      {/* Top Header & Connected Accounts Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            CONTENT FORGE
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Gen AI Platform for Content Regeneration
          </p>
        </div>

        <Button
          variant="outline"
          onClick={() => setIsAccountManagerOpen(true)}
          className="gap-2 self-start sm:self-auto border-gray-200 text-sm font-medium hover:bg-gray-50"
        >
          <Shield className="h-4 w-4 text-accent" />
          Connected Accounts ({accounts.length})
        </Button>
      </div>

      {bannerNotice && (
        <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
            <span>{bannerNotice}</span>
          </div>
          <button
            onClick={() => setBannerNotice(null)}
            className="text-xs font-semibold text-emerald-700 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <ContentSubmissionForm
        value={sourceContent}
        onChange={setSourceContent}
        mediaFile={mediaFile}
        onMediaFileChange={setMediaFile}
      />

      <OutputTypeSelector
        availableTypes={availableTypes}
        selected={selectedTypes}
        onChange={setSelectedTypes}
      />

      <GenerationControls params={params} onChange={setParams} />

      <div className="flex items-center gap-3">
        <Button onClick={handleGenerate} disabled={!canGenerate} className="gap-2">
          {generating ? (
            "Transforming Content..."
          ) : (
            <>
              <Sparkles className="h-4 w-4" /> Generate Deliverables
            </>
          )}
        </Button>
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>

      {Object.keys(results).length > 0 && (
        <div className="space-y-4 pt-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Generated Deliverables</h2>
            <p className="text-xs text-gray-500">Edit and publish deliverables independently</p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            {Object.entries(results).map(([type, result]) => (
              <OutputPreviewCard
                key={type}
                outputType={type}
                result={result}
                onPublishClick={(outputType, data) => setActivePublish({ outputType, data })}
              />
            ))}
          </div>
        </div>
      )}

      {/* Account Manager Modal */}
      <AccountManager
        isOpen={isAccountManagerOpen}
        onClose={() => setIsAccountManagerOpen(false)}
        accounts={accounts}
        onRefreshAccounts={refreshAccounts}
      />

      {/* Direct Publishing & Distribution Modal */}
      {activePublish && (
        <PublishModal
          isOpen={true}
          onClose={() => setActivePublish(null)}
          outputType={activePublish.outputType}
          initialData={activePublish.data}
          accounts={accounts}
          onOpenAccountManager={() => {
            setActivePublish(null);
            setIsAccountManagerOpen(true);
          }}
        />
      )}
    </main>
  );
}
