import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 text-center">
      <h1 className="text-3xl font-semibold text-gray-900">Content Transformation Platform</h1>
      <p className="max-w-md text-sm text-gray-500">
        Turn one source of content into every deliverable you need — advisories, social
        posts, briefings, presentations, and more.
      </p>
      <Link
        href="/dashboard"
        className="rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white hover:opacity-90"
      >
        Go to Dashboard
      </Link>
    </main>
  );
}
