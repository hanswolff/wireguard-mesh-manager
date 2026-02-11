interface SettingsMetricTileProps {
  label: string;
  children: React.ReactNode;
  layout?: 'stacked' | 'inline';
  labelClassName?: string;
}

export function SettingsMetricTile({
  label,
  children,
  layout = 'stacked',
  labelClassName,
}: SettingsMetricTileProps) {
  const isInline = layout === 'inline';
  const baseLabelClass = isInline
    ? 'text-sm font-medium'
    : 'text-sm font-medium text-muted-foreground';

  return (
    <div
      className={
        isInline
          ? 'flex items-center justify-between p-3 border rounded-lg'
          : 'p-3 border rounded-lg'
      }
    >
      <div className={labelClassName ?? baseLabelClass}>{label}</div>
      {children}
    </div>
  );
}
