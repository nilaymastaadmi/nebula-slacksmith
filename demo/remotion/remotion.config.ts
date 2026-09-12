import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setCodec('h264');
Config.setOverwriteOutput(true);

// Remotion otherwise downloads its own Chrome Headless Shell on first render.
// That download stalled here (storage.googleapis.com sent no data for 20 s), so
// point it at a Chrome that is already installed. Env var, not a hard-coded
// path: tools/env.sh makes the same argument about machine-specific constants.
//   REMOTION_BROWSER="C:\Program Files\Google\Chrome\Application\chrome.exe"
const browser = process.env.REMOTION_BROWSER;
if (browser) {
  Config.setBrowserExecutable(browser);
}
