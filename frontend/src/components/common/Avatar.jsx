import React, { useState } from 'react';

/**
 * Avatar: shows the user's profile photo when present, otherwise falls back to
 * their coloured initials. A broken/failed image also falls back to initials.
 */
const Avatar = ({ photo, initials = 'U', color = '#6B7280', size = 40, radius = '50%', fontSize, className = '', style = {} }) => {
  const [broken, setBroken] = useState(false);
  const base = {
    width: size,
    height: size,
    borderRadius: radius,
    flexShrink: 0,
    ...style,
  };

  if (photo && !broken) {
    return (
      <img
        src={photo}
        alt={initials}
        className={className}
        onError={() => setBroken(true)}
        style={{ ...base, objectFit: 'cover', display: 'block' }}
      />
    );
  }

  return (
    <div
      className={className}
      style={{
        ...base,
        background: color,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: fontSize || Math.round(size * 0.4),
      }}
    >
      {initials}
    </div>
  );
};

export default Avatar;
