import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

// The only animation in either card. 12 frames in, 12 frames out.
export const Fade: React.FC<{children: React.ReactNode}> = ({children}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const opacity = interpolate(
    frame,
    [0, 12, durationInFrames - 12, durationInFrames - 1],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  return <div style={{opacity, width: '100%', height: '100%'}}>{children}</div>;
};
