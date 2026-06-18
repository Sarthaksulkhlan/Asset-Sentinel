import React from "react";

interface SentinelLogoProps {
  className?: string;
  glow?: boolean;
}

export const SentinelLogo: React.FC<SentinelLogoProps> = ({
  className = "w-6 h-6",
  glow = true
}) => {
  return (
    <svg
      id="sentinel-svg-logo"
      viewBox="0 0 512 512"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${className} transition-all duration-300`}
    >
      <defs>
        {/* Neon Glow filters for premium visual feedback */}
        <filter id="sentinel-laser-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="8" result="blur1" />
          <feGaussianBlur stdDeviation="3" result="blur2" />
          <feMerge>
            <feMergeNode in="blur1" />
            <feMergeNode in="blur2" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Soft backlighting for the entire shield */}
        <filter id="sentinel-ambient-glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="15" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Linear Gradients matching the Cyber Aesthetic */}
        <linearGradient id="shield-gradient" x1="256" y1="40" x2="256" y2="470" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#00e5ff" />
          <stop offset="50%" stopColor="#0088ff" />
          <stop offset="100%" stopColor="#051c38" />
        </linearGradient>

        <linearGradient id="eye-gradient" x1="256" y1="170" x2="256" y2="362" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#00e5ff" />
          <stop offset="100%" stopColor="#0055ff" />
        </linearGradient>
      </defs>

      {/* Ambient background soft glow under the shield */}
      {glow && (
        <path
          d="M256,40 L120,80 C120,220 150,370 256,470 C362,370 392,220 392,80 Z"
          fill="#00d1ff"
          fillOpacity="0.06"
          filter="url(#sentinel-ambient-glow)"
        />
      )}

      {/* OUTER SHIELD FRAME - Highly Detailed Hex/Shield Hybrid with glowing neon stroke */}
      <path
        d="M256,35 L110,75 C110,230 145,390 256,495 C367,390 402,230 402,75 Z"
        stroke="url(#shield-gradient)"
        strokeWidth="10"
        strokeLinecap="round"
        strokeLinejoin="round"
        filter={glow ? "url(#sentinel-laser-glow)" : undefined}
      />

      {/* INNER SHIELD FRAME */}
      <path
        d="M256,58 L130,94 C130,224 160,364 256,458 C352,364 382,224 382,94 Z"
        stroke="#00d1ff"
        strokeWidth="2.5"
        strokeOpacity="0.5"
        strokeDasharray="16 8 4 8"
      />

      {/* MAIN CIRCUITRY TRACES (Motherboard channels radiating into the shield) */}
      <g stroke="#00d1ff" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.85">
        {/* Top Left Branch */}
        <path d="M190,130 L160,110 L160,82" />
        <path d="M210,130 L180,100 L180,78" />

        {/* Top Right Branch */}
        <path d="M322,130 L352,110 L352,82" />
        <path d="M302,130 L332,100 L332,78" />

        {/* Mid-Left Lateral Bus */}
        <path d="M140,256 L185,256 L205,276" />
        <path d="M150,225 L175,225 L190,240" />

        {/* Mid-Right Lateral Bus */}
        <path d="M372,256 L327,256 L307,276" />
        <path d="M362,225 L337,225 L322,240" />

        {/* Bottom Left Branch */}
        <path d="M180,310 L150,340 C150,380 162,410 180,430" />
        <path d="M210,345 L180,375 L180,395" />

        {/* Bottom Right Branch */}
        <path d="M332,310 L362,340 C362,380 350,410 332,430" />
        <path d="M302,345 L332,375 L332,395" />

        {/* Vertical Backbone */}
        <path d="M256,160 L256,70" />
        <path d="M256,365 L256,430" />
      </g>

      {/* CIRCUIT NODE TERMINAL PADS (Small circular copper/tin ports) */}
      <g fill="#00e5ff" filter={glow ? "url(#sentinel-laser-glow)" : undefined}>
        <circle cx="160" cy="82" r="6" />
        <circle cx="180" cy="78" r="6" />
        <circle cx="352" cy="82" r="6" />
        <circle cx="332" cy="78" r="6" />
        <circle cx="140" cy="256" r="6" />
        <circle cx="150" cy="225" r="5" />
        <circle cx="372" cy="256" r="6" />
        <circle cx="362" cy="225" r="5" />
        <circle cx="180" cy="430" r="6" />
        <circle cx="180" cy="395" r="5" />
        <circle cx="332" cy="430" r="6" />
        <circle cx="332" cy="395" r="5" />
        <circle cx="256" cy="70" r="6" />
      </g>

      {/* THE GUARDIAN CYBERNETIC EYE (Center focus piece of the platform) */}
      <g filter={glow ? "url(#sentinel-laser-glow)" : undefined}>
        {/* Outer Eyelid Shape */}
        <path
          d="M140,256 Q256,155 372,256 Q256,357 140,256 Z"
          fill="#051221"
          fillOpacity="0.8"
          stroke="url(#eye-gradient)"
          strokeWidth="7"
          strokeLinejoin="round"
        />

        {/* Eye Inner Lens Frame Ring */}
        <circle cx="256" cy="256" r="55" stroke="#00e5ff" strokeWidth="4.5" strokeDasharray="3 3" />
        <circle cx="256" cy="256" r="42" stroke="#0088ff" strokeWidth="2.5" />

        {/* Shimmer/Lens Refraction Horizontal Accents */}
        <path d="M165,256 H205" stroke="#00e5ff" strokeWidth="2" opacity="0.6" />
        <path d="M307,256 H347" stroke="#00e5ff" strokeWidth="2" opacity="0.6" />

        {/* Glowing Center Pupil & Iris */}
        <circle cx="256" cy="256" r="24" fill="url(#eye-gradient)" />
        <circle cx="256" cy="256" r="13" fill="#ffffff" filter="blur(1px)" />
        <circle cx="256" cy="256" r="6" fill="#ffffff" />

        {/* Sci-fi Target Reticle/Crosshair Overlay */}
        <path d="M256,236 V244" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
        <path d="M256,268 V276" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
        <path d="M236,256 H244" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
        <path d="M268,256 H276" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
      </g>
    </svg>
  );
};
