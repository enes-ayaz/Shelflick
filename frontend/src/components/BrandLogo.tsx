import React from "react";

interface BrandLogoProps {
  className?: string;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ className = "" }) => {
  return (
    <span className={`modern-logo-pill ${className}`.trim()} title="Library & Cinema">
      <span className="logo-core">
        <span className="book-pages-wrapper">
          <span className="page-line line-1" />
          <span className="page-line line-2" />
        </span>
        <span className="play-arrow" />
      </span>
      <span className="ambient-glow" />
    </span>
  );
};
