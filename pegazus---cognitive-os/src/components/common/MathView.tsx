import React, { useMemo } from 'react';
import katex from 'katex';

interface MathViewProps {
  math: string;
  display?: boolean;
  className?: string;
  ariaLabel?: string;
}

export const MathView: React.FC<MathViewProps> = ({
  math,
  display = false,
  className = '',
  ariaLabel
}) => {
  const html = useMemo(() => {
    try {
      return katex.renderToString(math, {
        displayMode: display,
        throwOnError: false,
        output: 'htmlAndMathml'
      });
    } catch {
      return math;
    }
  }, [math, display]);

  return (
    <span
      className={`inline-block font-mono select-text ${className}`}
      aria-label={ariaLabel || math}
      role="math"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};
