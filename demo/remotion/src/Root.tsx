import React from 'react';
import {Composition} from 'remotion';
import {End} from './End';
import {Title} from './Title';
import {CARD_FRAMES, FPS} from './facts';

// Exactly two compositions. No lower thirds, no callout graphics: every ZOOM
// TARGET in demo/SCRIPT.md is reached with Recordly's cursor zoom on the real
// terminal, per demo/VIDEO_PROMPT.md step 2.
export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Title"
      component={Title}
      durationInFrames={CARD_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
    <Composition
      id="End"
      component={End}
      durationInFrames={CARD_FRAMES}
      fps={FPS}
      width={1920}
      height={1080}
    />
  </>
);
