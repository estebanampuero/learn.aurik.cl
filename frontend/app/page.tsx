"use client";

import { useAuth } from "@/lib/auth";
import AuthGate from "@/components/AuthGate";
import AppShell from "@/components/AppShell";

export default function Page() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <>
        <div className="mesh-bg" />
        <div className="center-screen"><span className="spinner big" /></div>
      </>
    );
  }
  return (
    <>
      <div className="mesh-bg" />
      {user ? <AppShell /> : <AuthGate />}
    </>
  );
}
