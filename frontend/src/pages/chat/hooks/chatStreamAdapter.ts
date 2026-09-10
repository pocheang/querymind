export function createChatRunLifecycle() {
  let mounted = true;
  let activeRun: number | null = null;
  let nextRun = 0;
  return {
    mount(): void {
      mounted = true;
    },
    begin(): number | null {
      if (!mounted || activeRun !== null) return null;
      activeRun = ++nextRun;
      return activeRun;
    },
    isActive(run: number): boolean {
      return mounted && activeRun === run;
    },
    stop(run: number): void {
      if (activeRun === run) activeRun = null;
    },
    dispose(): void {
      mounted = false;
      activeRun = null;
    },
  };
}
