import React, { useState, useEffect } from 'react';

export type Units = 'metric' | 'imperial';

interface BasicSettingsProps {
  onChange?: (data: BasicSettingsState) => void;
}

export interface BasicSettingsState {
  palletLength: number;
  palletWidth: number;
  stackHeight: number;
  palletHeight: number;
  overhangSides: number;
  overhangEnds: number;
  units: Units;
  boxLength: number;
  boxWidth: number;
  boxHeight: number;
  boxWeight: number;
  labelOrientation: number;
  boxPadding: number;
  maxGrip: number;
  maxGripAuto: boolean;
}

const inchInMm = 25.4;
const orientations = [0, 90, 180, 270];

export function BasicSettings({ onChange }: BasicSettingsProps) {
  const [state, setState] = useState<BasicSettingsState>({
    palletLength: 1200,
    palletWidth: 800,
    stackHeight: 1405,
    palletHeight: 150,
    overhangSides: 0,
    overhangEnds: 0,
    units: 'metric',
    boxLength: 200,
    boxWidth: 200,
    boxHeight: 200,
    boxWeight: 1,
    labelOrientation: 0,
    boxPadding: 0,
    maxGrip: 1,
    maxGripAuto: true,
  });

  useEffect(() => {
    onChange && onChange(state);
  }, [state, onChange]);

  function update<K extends keyof BasicSettingsState>(key: K, value: BasicSettingsState[K]) {
    setState(prev => ({ ...prev, [key]: value }));
  }

  function handleUnitsChange(u: Units) {
    if (u === state.units) return;
    const factor = u === 'metric' ? inchInMm : 1 / inchInMm;
    update('units', u);
    update('palletLength', parseFloat((state.palletLength * factor).toFixed(2)));
    update('palletWidth', parseFloat((state.palletWidth * factor).toFixed(2)));
    update('stackHeight', parseFloat((state.stackHeight * factor).toFixed(2)));
    update('palletHeight', parseFloat((state.palletHeight * factor).toFixed(2)));
    update('overhangSides', parseFloat((state.overhangSides * factor).toFixed(2)));
    update('overhangEnds', parseFloat((state.overhangEnds * factor).toFixed(2)));
    update('boxLength', parseFloat((state.boxLength * factor).toFixed(2)));
    update('boxWidth', parseFloat((state.boxWidth * factor).toFixed(2)));
    update('boxHeight', parseFloat((state.boxHeight * factor).toFixed(2)));
    update('boxPadding', parseFloat((state.boxPadding * factor).toFixed(2)));
  }

  const uLabel = state.units === 'metric' ? 'mm' : 'in';
  const wLabel = state.units === 'metric' ? 'kg' : 'lb';

  function numInput(value: number, onChange: (v: number) => void, step = 1) {
    return (
      <input
        type="number"
        value={value}
        step={step}
        onChange={e => onChange(parseFloat(e.target.value))}
      />
    );
  }

  return (
    <div className="basic-settings">
      <h3>Paleta</h3>
      <label>
        Długość ({uLabel})
        {numInput(state.palletLength, v => update('palletLength', v))}
      </label>
      <label>
        Szerokość ({uLabel})
        {numInput(state.palletWidth, v => update('palletWidth', v))}
      </label>
      <label>
        Maks. wysokość stosu ({uLabel})
        {numInput(state.stackHeight, v => update('stackHeight', v))}
      </label>
      <label>
        Wysokość palety ({uLabel})
        {numInput(state.palletHeight, v => update('palletHeight', v))}
      </label>
      <label>
        Overhang boki ({uLabel})
        {numInput(state.overhangSides, v => update('overhangSides', v))}
      </label>
      <label>
        Overhang przód/tył ({uLabel})
        {numInput(state.overhangEnds, v => update('overhangEnds', v))}
      </label>
      <div>
        Jednostki:
        <select value={state.units} onChange={e => handleUnitsChange(e.target.value as Units)}>
          <option value="metric">metryczne</option>
          <option value="imperial">imperialne</option>
        </select>
      </div>
      <h3>Produkt</h3>
      <label>
        Długość pudełka ({uLabel})
        {numInput(state.boxLength, v => update('boxLength', v))}
      </label>
      <label>
        Szerokość pudełka ({uLabel})
        {numInput(state.boxWidth, v => update('boxWidth', v))}
      </label>
      <label>
        Wysokość pudełka ({uLabel})
        {numInput(state.boxHeight, v => update('boxHeight', v))}
      </label>
      <label>
        Waga pudełka ({wLabel})
        {numInput(state.boxWeight, v => update('boxWeight', v), 0.01)}
      </label>
      <label>
        Orientacja etykiety
        <select
          value={state.labelOrientation}
          onChange={e => update('labelOrientation', parseInt(e.target.value, 10))}
        >
          {orientations.map(o => (
            <option key={o} value={o}>{o}°</option>
          ))}
        </select>
      </label>
      <label>
        Padding ({uLabel})
        {numInput(state.boxPadding, v => update('boxPadding', v))}
      </label>
      <label>
        Max grip
        {numInput(state.maxGrip, v => update('maxGrip', v))}
      </label>
      <label>
        Auto group
        <input
          type="checkbox"
          checked={state.maxGripAuto}
          onChange={e => update('maxGripAuto', e.target.checked)}
        />
      </label>
    </div>
  );
}

export default BasicSettings;
