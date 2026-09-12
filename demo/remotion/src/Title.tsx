import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Fade} from './Fade';
import {ACCENT, AUTHORS, BG, INK, MUTED, PROJECT, SERIF, TRACK_LONG, TRACK_SHORT} from './facts';

export const Title: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: BG, fontFamily: SERIF}}>
    <Fade>
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'flex-start',
          padding: '0 140px',
        }}
      >
        <div style={{fontSize: 132, color: INK, letterSpacing: -1.5, lineHeight: 1}}>
          {PROJECT}
        </div>
        <div style={{width: 220, height: 3, backgroundColor: ACCENT, margin: '38px 0 34px'}} />
        <div style={{fontSize: 34, color: INK, marginBottom: 12}}>{TRACK_SHORT}</div>
        <div style={{fontSize: 30, color: MUTED, fontStyle: 'italic', maxWidth: 1250, lineHeight: 1.35}}>
          {TRACK_LONG}
        </div>
        <div style={{fontSize: 30, color: INK, marginTop: 54}}>{AUTHORS}</div>
      </AbsoluteFill>
    </Fade>
  </AbsoluteFill>
);
