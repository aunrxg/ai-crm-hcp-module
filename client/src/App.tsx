import HCPSelector from "./components/HCPSelector";

function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <HCPSelector />
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center gap-4 px-6 text-center">
        <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-4 py-1 text-sm text-cyan-300">
          React + TypeScript + Tailwind
        </span>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Client initialized successfully
        </h1>
        <p className="max-w-xl text-slate-300">
          Start building your frontend in <code className="rounded bg-slate-800 px-2 py-1">client/src</code>.
        </p>
        <div className="mt-2 rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm text-slate-300">
          Run <code className="rounded bg-slate-800 px-2 py-1">npm run dev</code> inside the{" "}
          <code className="rounded bg-slate-800 px-2 py-1">client</code> folder.
        </div>
      </div>
    </main>
  )
}

export default App
