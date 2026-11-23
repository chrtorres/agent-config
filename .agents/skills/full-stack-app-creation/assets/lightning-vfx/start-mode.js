/** Which mode a page load opens in when one mode is the main game and another its tutorial.
 * Order: an explicit ?<param>=<mode>; automation keeps the tutorial so suites written for
 * the old default keep their contracts (?<param>=player opts automation into the real rule);
 * a player with no main-mode save opens the main mode; otherwise the save's active flag decides. */
export function resolveStartMode({
  params, webdriver = false, mainSave = null, main = "main", tutorial = "tutorial", param = "start",
}) {
  const requested = params?.get?.(param);
  if (requested === main || requested === tutorial) return requested;
  if (webdriver && requested !== "player") return tutorial;
  if (mainSave == null) return main;
  try {
    return JSON.parse(mainSave)?.active === true ? main : tutorial;
  } catch {
    return main;
  }
}
