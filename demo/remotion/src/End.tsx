import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Fade} from './Fade';
import {ACCENT, BG, INK, MUTED, PROJECT, REPO_URL, SERIF} from './facts';

export const End: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: BG, fontFamily: SERIF}}>
    <Fade>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: '0 120px'}}>
        <div style={{fontSize: 40, color: MUTED, marginBottom: 30}}>{PROJECT}</div>
        <div style={{width: 220, height: 3, backgroundColor: ACCENT, marginBottom: 42}} />
        <div style={{fontSize: 52, color: INK, textAlign: 'center', lineHeight: 1.3}}>
          {REPO_URL}
        </div>
      </AbsoluteFill>
    </Fade>
  </AbsoluteFill>
);
