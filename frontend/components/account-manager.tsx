"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  getAuthorizationUrl,
  disconnectAccount,
  type ConnectedAccount,
} from "@/lib/api-client";
import { ShieldCheck, Plus, Trash2, Loader2, Info, ExternalLink, Mail } from "lucide-react";

interface AccountManagerProps {
  isOpen: boolean;
  onClose: () => void;
  accounts: ConnectedAccount[];
  onRefreshAccounts: () => Promise<void>;
}

type Platform = "linkedin" | "gmail";

const PLATFORM_LABELS: Record<Platform, string> = {
  linkedin: "LinkedIn",
  gmail: "Gmail",
};

const PLATFORM_VARS: Record<Platform, string[]> = {
  linkedin: ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
  gmail: ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
};

const PLATFORM_PORTAL: Record<Platform, string> = {
  linkedin: "https://www.linkedin.com/developers/",
  gmail: "https://console.cloud.google.com/apis/credentials",
};

export default function AccountManager({
  isOpen,
  onClose,
  accounts,
  onRefreshAccounts,
}: AccountManagerProps) {
  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [missingConfig, setMissingConfig] = useState<{
    platform: Platform;
    vars: string[];
    portalUrl: string;
    redirectUri: string;
  } | null>(null);

  if (!isOpen) return null;

  async function handleConnect(platform: Platform) {
    setConnectingPlatform(platform);
    setError(null);
    setMissingConfig(null);

    try {
      const data = await getAuthorizationUrl(platform);

      if (data.is_configured && data.authorization_url) {
        window.location.href = data.authorization_url;
      } else {
        setConnectingPlatform(null);
        setMissingConfig({
          platform,
          vars: PLATFORM_VARS[platform],
          portalUrl: PLATFORM_PORTAL[platform],
          redirectUri: `http://localhost:8000/api/auth/${platform}/callback`,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to connect ${platform}`);
      setConnectingPlatform(null);
    }
  }

  async function handleDisconnect(accountId: string) {
    setDeletingId(accountId);
    setError(null);
    try {
      await disconnectAccount(accountId);
      await onRefreshAccounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect account");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-accent" />
            <h2 className="text-lg font-semibold text-gray-900">Connected Accounts</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          <p className="text-xs text-gray-500 leading-relaxed">
            Connect your social media and email accounts to enable direct 1-click publishing.
            Tokens are encrypted using AES-128/Fernet at rest and scoped strictly to your session.
          </p>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              {error}
            </div>
          )}

          {/* Missing OAuth Credentials Guidance Alert */}
          {missingConfig && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-3">
              <div className="flex items-start gap-2 text-amber-900">
                <Info className="h-4 w-4 mt-0.5 flex-shrink-0 text-amber-600" />
                <div className="text-xs space-y-1">
                  <p className="font-semibold">
                    {PLATFORM_LABELS[missingConfig.platform]} API Keys Needed for Live Login
                  </p>
                  <p className="text-amber-800 leading-relaxed">
                    To redirect to the official login page, add these variables to your{" "}
                    <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[11px]">backend/.env</code> file:
                  </p>
                  <ul className="list-disc pl-4 font-mono text-[11px] text-amber-900">
                    {missingConfig.vars.map((v) => (
                      <li key={v}>{v}=your_key_here</li>
                    ))}
                  </ul>
                  <p className="pt-1 text-amber-800">
                    Set Redirect URI in the developer console to:{" "}
                    <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[10px] break-all">
                      {missingConfig.redirectUri}
                    </code>
                  </p>
                  {missingConfig.platform === "gmail" && (
                    <p className="pt-1 text-amber-800">
                      Also enable the <strong>Gmail API</strong> and add{" "}
                      <code className="bg-amber-100 px-1 py-0.5 rounded font-mono text-[10px]">gmail.send</code>{" "}
                      scope on the OAuth consent screen.
                    </p>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-amber-200/60">
                <a
                  href={missingConfig.portalUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded bg-white border border-amber-300 px-2.5 py-1 text-xs font-medium text-amber-900 hover:bg-amber-100"
                >
                  {missingConfig.platform === "gmail" ? "Google Cloud Console" : "Developer Portal"}{" "}
                  <ExternalLink className="h-3 w-3" />
                </a>
                <button
                  type="button"
                  onClick={() => setMissingConfig(null)}
                  className="text-xs text-gray-500 hover:underline ml-auto"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Connected Accounts List */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-600">Active Connections</h3>
            {accounts.length === 0 ? (
              <p className="rounded-lg border border-dashed border-gray-200 p-4 text-center text-sm text-gray-400">
                No accounts connected yet. Connect your LinkedIn or Gmail account below.
              </p>
            ) : (
              <div className="divide-y rounded-lg border border-gray-200">
                {accounts.map((acc) => (
                  <div key={acc.id} className="flex items-center justify-between p-3.5">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm text-gray-900">{acc.account_name}</span>
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-gray-600">
                          {PLATFORM_LABELS[acc.platform] ?? acc.platform}
                        </span>
                      </div>
                      {acc.account_handle && (
                        <p className="text-xs text-gray-400">{acc.account_handle}</p>
                      )}
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDisconnect(acc.id)}
                      disabled={deletingId === acc.id}
                      className="text-red-600 hover:bg-red-50 hover:text-red-700 border-gray-200"
                    >
                      {deletingId === acc.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Connect New Account Options */}
          <div className="space-y-3 pt-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-600">Add Account</h3>
            <div className="grid grid-cols-2 gap-3">
              <Button
                variant="outline"
                onClick={() => handleConnect("linkedin")}
                disabled={connectingPlatform !== null}
                className="gap-2 justify-center"
              >
                {connectingPlatform === "linkedin" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4 text-accent" />
                )}
                LinkedIn
              </Button>

              <Button
                variant="outline"
                onClick={() => handleConnect("gmail")}
                disabled={connectingPlatform !== null}
                className="gap-2 justify-center"
              >
                {connectingPlatform === "gmail" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Mail className="h-4 w-4 text-accent" />
                )}
                Gmail
              </Button>
            </div>
          </div>

          <div className="flex justify-end pt-2 border-t">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
