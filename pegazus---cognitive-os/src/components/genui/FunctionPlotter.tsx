import React, { useState, useMemo } from 'react';
import { Sliders } from 'lucide-react';
import { MathView } from '../common/MathView';

interface FunctionPlotterProps {
  initialA?: number;
  initialB?: number;
  initialC?: number;
  type?: 'quadratic' | 'sine';
  title?: string;
}

export const FunctionPlotter: React.FC<FunctionPlotterProps> = ({
  initialA = 1,
  initialB = 0,
  initialC = -4,
  type = 'quadratic',
  title = 'f(x) = ax^2 + bx + c'
}) => {
  const [a, setA] = useState<number>(initialA);
  const [b, setB] = useState<number>(initialB);
  const [c, setC] = useState<number>(initialC);

  // SVG coordinate system mapping: viewBox = -10 to 10 for x, -10 to 10 for y
  const width = 360;
  const height = 240;
  const xMin = -8;
  const xMax = 8;
  const yMin = -8;
  const yMax = 8;

  const toSvgX = (x: number) => ((x - xMin) / (xMax - xMin)) * width;
  const toSvgY = (y: number) => height - ((y - yMin) / (yMax - yMin)) * height;

  const points = useMemo(() => {
    const pts: string[] = [];
    const steps = 120;
    for (let i = 0; i <= steps; i++) {
      const x = xMin + (i / steps) * (xMax - xMin);
      let y = 0;
      if (type === 'quadratic') {
        y = a * x * x + b * x + c;
      } else {
        y = a * Math.sin(b * x) + c;
      }
      if (!isNaN(y) && isFinite(y)) {
        // clamp to keep SVG path clean
        const clampedY = Math.max(yMin - 5, Math.min(yMax + 5, y));
        pts.push(`${toSvgX(x).toFixed(1)},${toSvgY(clampedY).toFixed(1)}`);
      }
    }
    return pts.join(' ');
  }, [a, b, c, type]);

  // Intercepts calculation for accessibility SR text
  const srDescription = useMemo(() => {
    if (type === 'quadratic') {
      const disc = b * b - 4 * a * c;
      let rootsText = 'No real roots';
      if (disc > 0 && a !== 0) {
        const r1 = ((-b + Math.sqrt(disc)) / (2 * a)).toFixed(2);
        const r2 = ((-b - Math.sqrt(disc)) / (2 * a)).toFixed(2);
        rootsText = `Roots at x = ${r1} and x = ${r2}`;
      } else if (disc === 0 && a !== 0) {
        rootsText = `Single root at x = ${(-b / (2 * a)).toFixed(2)}`;
      }
      return `Plot of f(x) = ${a}x^2 + ${b}x + ${c}. Y-intercept at (0, ${c}). ${rootsText}.`;
    }
    return `Plot of f(x) = ${a} sin(${b}x) + ${c}. Y-intercept at (0, ${c}). Amplitude ${Math.abs(a)}.`;
  }, [a, b, c, type]);

  return (
    <div className="p-4 rounded-2xl bg-[#0F172A] border border-slate-800 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Interactive Function Plotter
          </span>
        </div>
        <div className="text-sm font-mono text-indigo-300">
          <MathView
            math={
              type === 'quadratic'
                ? `f(x) = ${a === 1 ? '' : a === -1 ? '-' : a}x^2 ${b >= 0 ? '+' : ''}${b}x ${c >= 0 ? '+' : ''}${c}`
                : `f(x) = ${a}\\sin(${b}x) ${c >= 0 ? '+' : ''}${c}`
            }
          />
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full bg-[#090D16] border border-slate-800 rounded-xl overflow-hidden flex items-center justify-center">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-44 sm:h-52"
          role="img"
          aria-label={srDescription}
        >
          {/* Grid lines */}
          <g stroke="#1E293B" strokeWidth="1">
            {[-6, -4, -2, 2, 4, 6].map((gridX) => (
              <line
                key={`gx-${gridX}`}
                x1={toSvgX(gridX)}
                y1={0}
                x2={toSvgX(gridX)}
                y2={height}
              />
            ))}
            {[-6, -4, -2, 2, 4, 6].map((gridY) => (
              <line
                key={`gy-${gridY}`}
                x1={0}
                y1={toSvgY(gridY)}
                x2={width}
                y2={toSvgY(gridY)}
              />
            ))}
          </g>

          {/* Coordinate Axes */}
          <line
            x1={0}
            y1={toSvgY(0)}
            x2={width}
            y2={toSvgY(0)}
            stroke="#334155"
            strokeWidth="1.5"
          />
          <line
            x1={toSvgX(0)}
            y1={0}
            x2={toSvgX(0)}
            y2={height}
            stroke="#334155"
            strokeWidth="1.5"
          />

          {/* Function Curve */}
          <polyline
            fill="none"
            stroke="#14B8A6"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={points}
          />

          {/* Y-intercept marker */}
          <circle
            cx={toSvgX(0)}
            cy={toSvgY(c)}
            r="4"
            fill="#6366F1"
            stroke="#090D16"
            strokeWidth="2"
          />
        </svg>
      </div>

      {/* Sliders under graph */}
      <div className="grid grid-cols-3 gap-3 pt-1">
        <div>
          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
            <span>a (curve)</span>
            <span className="text-slate-200">{a}</span>
          </div>
          <input
            type="range"
            min="-4"
            max="4"
            step="0.5"
            value={a}
            onChange={(e) => setA(parseFloat(e.target.value))}
            aria-label="Coefficient a"
            className="w-full accent-indigo-500 h-1.5 bg-[#1E293B] rounded-lg cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
            <span>b (shift)</span>
            <span className="text-slate-200">{b}</span>
          </div>
          <input
            type="range"
            min="-5"
            max="5"
            step="1"
            value={b}
            onChange={(e) => setB(parseFloat(e.target.value))}
            aria-label="Coefficient b"
            className="w-full accent-indigo-500 h-1.5 bg-[#1E293B] rounded-lg cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
            <span>c (offset)</span>
            <span className="text-slate-200">{c}</span>
          </div>
          <input
            type="range"
            min="-6"
            max="6"
            step="1"
            value={c}
            onChange={(e) => setC(parseFloat(e.target.value))}
            aria-label="Constant c"
            className="w-full accent-indigo-500 h-1.5 bg-[#1E293B] rounded-lg cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
};
