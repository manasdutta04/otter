/**
 * Line-based y/n (no raw mode) — avoids Windows/ConPTY duplicate key ghosts.
 */

let chain: Promise<unknown> = Promise.resolve();

export async function confirmYn(question: string, defaultYes = false): Promise<boolean> {
  if (!process.stdin.isTTY) {
    return defaultYes;
  }

  const run = async (): Promise<boolean> => {
    const hint = defaultYes ? "[Y/n]" : "[y/N]";
    const readline = await import("node:readline");

    // Ensure we're not in raw mode leftover from anything else.
    if (typeof process.stdin.setRawMode === "function") {
      try {
        process.stdin.setRawMode(false);
      } catch {
        /* ignore */
      }
    }

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });

    try {
      const answer = await new Promise<string>((resolve) => {
        rl.question(`${question} ${hint} `, (a) => resolve(a));
      });
      const cleaned = answer.trim().toLowerCase();
      // "yy" / "yyy" from sticky keys → treat leading y/n only
      if (!cleaned) return defaultYes;
      if (cleaned.startsWith("y")) return true;
      if (cleaned.startsWith("n")) return false;
      return defaultYes;
    } finally {
      rl.close();
    }
  };

  const result = chain.then(run, run);
  chain = result.then(
    () => undefined,
    () => undefined,
  );
  return result;
}
