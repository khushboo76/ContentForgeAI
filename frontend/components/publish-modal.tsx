"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  publishToLinkedIn,
  sendEmailDeliverable,
  type ConnectedAccount,
} from "@/lib/api-client";
import { OUTPUT_TYPE_LABELS } from "@/lib/constants";
import { ExternalLink, CheckCircle2, AlertCircle, Loader2, Mail, Send } from "lucide-react";

type Channel = "linkedin" | "email";

interface PublishModalProps {
  isOpen: boolean;
  onClose: () => void;
  outputType: string;
  initialData: Record<string, unknown>;
  accounts: ConnectedAccount[];
  onOpenAccountManager: () => void;
}

export default function PublishModal({
  isOpen,
  onClose,
  outputType,
  initialData,
  accounts,
  onOpenAccountManager,
}: PublishModalProps) {
  const [channel, setChannel] = useState<Channel>("linkedin");

  // Form states
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [gmailAccountId, setGmailAccountId] = useState<string>("");
  const [linkedinText, setLinkedinText] = useState("");
  const [emailRecipients, setEmailRecipients] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");

  // Confirmation & Publishing states
  const [confirmed, setConfirmed] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishStatus, setPublishStatus] = useState<"idle" | "success" | "error">("idle");
  const [successInfo, setSuccessInfo] = useState<{ url?: string; message?: string } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Initialize content whenever modal opens or deliverable changes
  useEffect(() => {
    if (!isOpen) return;

    // Reset status
    setPublishStatus("idle");
    setErrorMessage(null);
    setSuccessInfo(null);
    setConfirmed(false);

    // Default channel
    if (outputType === "linkedin_post") {
      setChannel("linkedin");
    } else {
      setChannel("email");
    }

    let preparedLinkedInText = "";

    // Prepare LinkedIn text
    if (outputType === "linkedin_post") {
      const parts = [
        String(initialData.hook || "").trim(),
        String(initialData.body || "").trim(),
        Array.isArray(initialData.hashtags) ? (initialData.hashtags as string[]).join(" ") : "",
        initialData.cta ? `\n${String(initialData.cta).trim()}` : "",
      ].filter(Boolean);
      preparedLinkedInText = parts.join("\n\n");
      setLinkedinText(preparedLinkedInText);
    } else {
      setLinkedinText(JSON.stringify(initialData, null, 2));
    }

    // Prepare Email content
    const label = OUTPUT_TYPE_LABELS[outputType] ?? outputType;
    if (outputType === "email") {
      setEmailSubject(String(initialData.subject || `[${label}] Executive Deliverable`));
      setEmailBody(String(initialData.body || "").trim());
    } else if (outputType === "advisory") {
      setEmailSubject(`[${label}] Executive Deliverable`);
      setEmailBody(
        `SEVERITY: ${initialData.severity}\n\nSITUATION:\n${initialData.situation}\n\nIMPACT:\n${initialData.impact}\n\nRECOMMENDED ACTIONS:\n` +
          ((initialData.recommended_actions as string[]) || []).map((a) => `- ${a}`).join("\n")
      );
    } else if (outputType === "executive_summary") {
      setEmailSubject(`[${label}] Executive Deliverable`);
      setEmailBody(
        `SUMMARY:\n${initialData.summary}\n\nKEY FINDINGS:\n` +
          ((initialData.key_findings as string[]) || []).map((f) => `- ${f}`).join("\n") +
          (initialData.recommendations
            ? `\n\nRECOMMENDATIONS:\n` + ((initialData.recommendations as string[]) || []).map((r) => `- ${r}`).join("\n")
            : "")
      );
    } else if (outputType === "linkedin_post") {
      setEmailSubject(`[${label}] Executive Deliverable`);
      setEmailBody(preparedLinkedInText);
    } else {
      setEmailSubject(`[${label}] Executive Deliverable`);
      setEmailBody(JSON.stringify(initialData, null, 2));
    }
  }, [isOpen, outputType, initialData]);

  // Set default selected account when channel or accounts change
  useEffect(() => {
    if (channel === "email") {
      const gmailAccounts = accounts.filter((a) => a.platform === "gmail");
      if (gmailAccounts.length > 0) {
        if (!gmailAccounts.some((a) => a.id === gmailAccountId)) {
          setGmailAccountId(gmailAccounts[0].id);
        }
      } else {
        setGmailAccountId("");
      }
    } else {
      const matchingAccounts = accounts.filter((a) => a.platform === channel);
      if (matchingAccounts.length > 0) {
        if (!matchingAccounts.some((a) => a.id === selectedAccountId)) {
          setSelectedAccountId(matchingAccounts[0].id);
        }
      } else {
        setSelectedAccountId("");
      }
    }
  }, [channel, accounts, selectedAccountId, gmailAccountId]);

  if (!isOpen) return null;

  const filteredAccounts = accounts.filter((a) => a.platform === channel);
  const selectedAccount = accounts.find((a) => a.id === selectedAccountId);
  const gmailAccounts = accounts.filter((a) => a.platform === "gmail");
  const selectedGmailAccount = accounts.find((a) => a.id === gmailAccountId);
  const needsGmailReconnect =
    channel === "email" &&
    publishStatus === "error" &&
    Boolean(errorMessage?.toLowerCase().includes("gmail connection has expired"));

  async function handlePublish() {
    setPublishing(true);
    setErrorMessage(null);
    setPublishStatus("idle");

    try {
      if (channel === "linkedin") {
        if (!selectedAccountId) throw new Error("Please connect and select a LinkedIn account");
        if (!linkedinText.trim()) throw new Error("Post text cannot be empty");

        const res = await publishToLinkedIn({
          account_id: selectedAccountId,
          text: linkedinText,
          output_type: outputType,
        });
        setSuccessInfo({
          url: res.url,
          message: res.mode === "simulated" ? "Post published in simulation mode." : "Post published to LinkedIn!",
        });
        setPublishStatus("success");
      } else if (channel === "email") {
        const recipientsList = emailRecipients
          .split(",")
          .map((r) => r.trim())
          .filter(Boolean);
        if (recipientsList.length === 0) throw new Error("Please provide at least one recipient email");
        if (!emailSubject.trim()) throw new Error("Subject line is required");
        if (!emailBody.trim()) throw new Error("Email body cannot be empty");

        const res = await sendEmailDeliverable({
          account_id: gmailAccountId,
          recipients: recipientsList,
          subject: emailSubject,
          body_text: emailBody,
          output_type: outputType,
        });
        setSuccessInfo({
          message: selectedGmailAccount
            ? `Email sent via Gmail (${selectedGmailAccount.account_handle ?? selectedGmailAccount.account_name}) to ${recipientsList.join(", ")}`
            : `Email sent to ${recipientsList.join(", ")}`,
        });
        setPublishStatus("success");
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Publishing failed");
      setPublishStatus("error");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Publish & Distribute Content</h2>
            <p className="text-xs text-gray-500">
              Source Deliverable: <span className="font-medium text-gray-700">{OUTPUT_TYPE_LABELS[outputType] ?? outputType}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Channel Selector */}
          <div>
            <label className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Select Channel</label>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setChannel("linkedin");
                  setPublishStatus("idle");
                  setErrorMessage(null);
                }}
                className={`rounded-lg border p-3 text-center text-sm font-medium transition ${
                  channel === "linkedin"
                    ? "border-accent bg-accent/10 text-accent font-semibold"
                    : "border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                LinkedIn
              </button>
              <button
                type="button"
                onClick={() => {
                  setChannel("email");
                  setPublishStatus("idle");
                  setErrorMessage(null);
                }}
                className={`rounded-lg border p-3 text-center text-sm font-medium transition ${
                  channel === "email"
                    ? "border-accent bg-accent/10 text-accent font-semibold"
                    : "border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                Email
              </button>
            </div>
          </div>

          {/* Account Selector (for LinkedIn) */}
          {channel !== "email" && (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-gray-700">
                  Select LinkedIn Account
                </label>
                <button
                  type="button"
                  onClick={onOpenAccountManager}
                  className="text-xs text-accent hover:underline font-medium"
                >
                  Manage Accounts
                </button>
              </div>

              {filteredAccounts.length > 0 ? (
                <select
                  value={selectedAccountId}
                  onChange={(e) => setSelectedAccountId(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
                >
                  {filteredAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.account_name} {acc.account_handle ? `(${acc.account_handle})` : ""}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="flex items-center justify-between py-2 text-sm text-gray-500">
                  <span>No LinkedIn account connected yet.</span>
                  <Button size="sm" variant="outline" onClick={onOpenAccountManager}>
                    Connect Account
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Editor & Preview Area */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Preview & Edit Deliverable
              </label>
              {channel === "linkedin" && (
                <span className="text-xs text-gray-400">{linkedinText.length} characters</span>
              )}
            </div>

            {/* LinkedIn Editor */}
            {channel === "linkedin" && (
              <textarea
                rows={8}
                value={linkedinText}
                onChange={(e) => setLinkedinText(e.target.value)}
                placeholder="Draft your LinkedIn post..."
                className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40 font-normal leading-relaxed"
              />
            )}

            {/* Email Editor */}
            {channel === "email" && (
              <div className="space-y-3">
                {/* Gmail sender selector */}
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-medium text-gray-700">Send Via (Gmail Account)</label>
                    <button
                      type="button"
                      onClick={onOpenAccountManager}
                      className="text-xs text-accent hover:underline font-medium"
                    >
                      Manage Accounts
                    </button>
                  </div>
                  {gmailAccounts.length > 0 ? (
                    <select
                      value={gmailAccountId}
                      onChange={(e) => setGmailAccountId(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
                    >
                      {gmailAccounts.map((acc) => (
                        <option key={acc.id} value={acc.id}>
                          {acc.account_name} ({acc.account_handle ?? acc.account_name})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="flex items-center justify-between py-1 text-xs text-gray-500">
                      <span>No Gmail account connected. Connect Gmail to send a real email.</span>
                      <Button size="sm" variant="outline" onClick={onOpenAccountManager}>
                        Connect Gmail
                      </Button>
                    </div>
                  )}
                  {gmailAccountId && selectedGmailAccount && (
                    <p className="mt-1.5 text-[11px] text-emerald-700 font-medium">
                      ✓ Sending via Gmail API as {selectedGmailAccount.account_handle ?? selectedGmailAccount.account_name}
                    </p>
                  )}
                </div>

                <div>
                  <label className="text-xs text-gray-500">Recipients (comma-separated)</label>
                  <input
                    type="text"
                    value={emailRecipients}
                    onChange={(e) => setEmailRecipients(e.target.value)}
                    placeholder="stakeholders@example.com, leadership@example.com"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Subject</label>
                  <input
                    type="text"
                    value={emailSubject}
                    onChange={(e) => setEmailSubject(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Email Body (Markdown / Plain Text)</label>
                  <textarea
                    rows={8}
                    value={emailBody}
                    onChange={(e) => setEmailBody(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Confirmation Checkbox */}
          <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3">
            <label className="flex items-start gap-2.5 cursor-pointer text-xs text-amber-900 leading-snug">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-0.5 rounded text-accent focus:ring-accent"
              />
              <span>
                <strong>Confirmation:</strong> I have reviewed and verified this content. I confirm that I want to
                {channel === "email" ? " dispatch this email" : " publish this directly to my LinkedIn account"}.
              </span>
            </label>
          </div>

          {/* Publishing Status & Feedback */}
          {publishStatus === "success" && (
            <div className="flex items-start gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-800">
              <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-emerald-600 mt-0.5" />
              <div className="flex-1 text-sm">
                <p className="font-semibold">{successInfo?.message ?? "Successfully Published!"}</p>
                {successInfo?.url && (
                  <a
                    href={successInfo.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-flex items-center gap-1 font-medium text-emerald-700 underline hover:text-emerald-900"
                  >
                    View Live Post <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            </div>
          )}

          {publishStatus === "error" && (
            <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
              <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600 mt-0.5" />
              <div className="flex-1 text-sm">
                <p className="font-semibold">Publication Failed</p>
                <p className="text-xs text-red-700 mt-0.5">{errorMessage}</p>
                {needsGmailReconnect && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={onOpenAccountManager}
                    className="mt-3 border-red-300 bg-white text-red-700 hover:bg-red-100"
                  >
                    Reconnect Gmail
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="outline" onClick={onClose} disabled={publishing}>
              {publishStatus === "success" ? "Done" : "Cancel"}
            </Button>
            <Button
              onClick={handlePublish}
              disabled={publishing || !confirmed || (channel === "email" ? !gmailAccountId : !selectedAccountId)}
              className="gap-2"
            >
              {publishing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Publishing...
                </>
              ) : channel === "email" ? (
                <>
                  <Mail className="h-4 w-4" /> Send Email
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" /> Publish Now
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
