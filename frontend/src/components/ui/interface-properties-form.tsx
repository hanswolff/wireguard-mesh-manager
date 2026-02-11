import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Trash2, Info, AlertCircle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface InterfaceProperty {
  key: string;
  value: string;
}

interface InterfacePropertiesFormProps {
  value?: Record<string, unknown> | null;
  onChange: (properties: Record<string, unknown> | null) => void;
  disabled?: boolean;
  level: 'network' | 'location' | 'device';
}

const commonProperties = [
  {
    key: 'MTU',
    description: 'Maximum Transmission Unit (e.g., 1420, 1280)',
  },
  {
    key: 'Address',
    description: 'Interface IP address (e.g., 192.168.1.1/24)',
  },
  { key: 'ListenPort', description: 'Port to listen on (e.g., 51820)' },
  { key: 'PostUp', description: 'Command to run after interface is up' },
  { key: 'PostDown', description: 'Command to run after interface is down' },
  { key: 'Table', description: 'Routing table to use' },
  { key: 'FwMark', description: 'Firewall mark for packets' },
  { key: 'SaveConfig', description: 'Auto-save configuration (true/false)' },
];

export function InterfacePropertiesForm({
  value,
  onChange,
  disabled = false,
  level,
}: InterfacePropertiesFormProps) {
  const [properties, setProperties] = useState<InterfaceProperty[]>(
    value
      ? Object.entries(value).map(([key, value]) => ({
          key,
          value: String(value),
        }))
      : []
  );
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [validationErrors, setValidationErrors] = useState<Record<number, string>>({});
  const [newValidationError, setNewValidationError] = useState<string | null>(null);

  // Sync properties state with value prop changes when value actually changes
  // This is intentional: we need to update local state when parent data changes (e.g., device loads in edit mode)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const newProperties = value
      ? Object.entries(value).map(([key, value]) => ({
          key,
          value: String(value),
        }))
      : [];
    setProperties(newProperties);
    setValidationErrors({});
    setNewValidationError(null);
  }, [value]);

  const validatePropertyValue = (value: string): string | null => {
    if (value.includes('\n') || value.includes('\r')) {
      return 'Property values cannot contain line breaks';
    }
    return null;
  };

  const addProperty = () => {
    if (newKey && newValue) {
      const validationError = validatePropertyValue(newValue);
      if (validationError) {
        setNewValidationError(validationError);
        return;
      }
      setNewValidationError(null);

      const updated = [...properties, { key: newKey, value: newValue }];
      setProperties(updated);
      onChange(
        updated.reduce((acc, { key, value }) => ({ ...acc, [key]: value }), {})
      );
      setNewKey('');
      setNewValue('');
    }
  };

  const removeProperty = (index: number) => {
    const updated = properties.filter((_, i) => i !== index);
    setProperties(updated);
    if (updated.length === 0) {
      onChange(null);
    } else {
      onChange(
        updated.reduce((acc, { key, value }) => ({ ...acc, [key]: value }), {})
      );
    }
  };

  const updateProperty = (
    index: number,
    field: 'key' | 'value',
    value: string
  ) => {
    if (field === 'value') {
      const validationError = validatePropertyValue(value);
      if (validationError) {
        setValidationErrors((prev) => ({ ...prev, [index]: validationError }));
        return;
      }
    }

    // Clear validation error if it exists
    setValidationErrors((prev) => {
      const next = { ...prev };
      delete next[index];
      return next;
    });

    const updated = properties.map((prop, i) =>
      i === index ? { ...prop, [field]: value } : prop
    );
    setProperties(updated);
    onChange(
      updated.reduce((acc, { key, value }) => ({ ...acc, [key]: value }), {})
    );
  };

  const addCommonProperty = (key: string) => {
    if (!properties.find((p) => p.key === key)) {
      const updated = [...properties, { key, value: '' }];
      setProperties(updated);
      onChange(
        updated.reduce((acc, { key, value }) => ({ ...acc, [key]: value }), {})
      );
    }
  };

  const levelDescription = {
    network:
      'Network-level properties are inherited by all locations and devices in this network',
    location:
      'Location-level properties override network settings and are inherited by devices in this location',
    device:
      'Device-level properties override both network and location settings for this specific device',
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Interface Properties</CardTitle>
            <CardDescription className="mt-1">
              {levelDescription[level]}
            </CardDescription>
          </div>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p>
                  These properties will be added to the [Interface] section of
                  the WireGuard configuration. Common properties include
                  Address, ListenPort, PostUp, and PostDown commands.
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Common Properties Quick Add */}
        <div>
          <Label className="text-sm font-medium">Common Properties</Label>
          <div className="flex flex-wrap gap-2 mt-2">
            {commonProperties.map((prop) => (
              <TooltipProvider key={prop.key}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => addCommonProperty(prop.key)}
                      disabled={
                        disabled || properties.some((p) => p.key === prop.key)
                      }
                    >
                      {prop.key}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{prop.description}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ))}
          </div>
        </div>

        {/* Existing Properties */}
        {properties.length > 0 && (
          <div className="space-y-2">
            <Label className="text-sm font-medium">Current Properties</Label>
            {properties.map((prop, index) => (
              <div key={index} className="flex gap-2 items-start">
                <Input
                  value={prop.key}
                  onChange={(e) => updateProperty(index, 'key', e.target.value)}
                  placeholder="Property key"
                  disabled={disabled}
                  className="flex-[2] min-w-[200px]"
                />
                <div className="flex-1 flex flex-col gap-1">
                  <Textarea
                    value={prop.value}
                    onChange={(e) =>
                      updateProperty(index, 'value', e.target.value)
                    }
                    placeholder="Property value"
                    disabled={disabled}
                    className="min-h-[40px] resize-y"
                    rows={1}
                  />
                  {validationErrors[index] && (
                    <p className="text-xs text-destructive flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {validationErrors[index]}
                    </p>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => removeProperty(index)}
                  disabled={disabled}
                  className="self-start"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}

        {/* Add New Property */}
        <div className="space-y-2">
          <Label className="text-sm font-medium">Add Custom Property</Label>
          <div className="flex gap-2 items-start">
            <Input
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder="Property key"
              disabled={disabled}
              className="flex-[2] min-w-[200px]"
            />
            <div className="flex-1 flex flex-col gap-1">
              <Textarea
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                placeholder="Property value"
                disabled={disabled}
                className="min-h-[40px] resize-y"
                rows={1}
              />
              {newValidationError && (
                <p className="text-xs text-destructive flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {newValidationError}
                </p>
              )}
            </div>
            <Button
              onClick={addProperty}
              disabled={disabled || !newKey || !newValue}
              size="icon"
              className="self-start"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Example Display */}
        <div className="mt-4 p-3 bg-muted rounded-md">
          <p className="text-sm font-mono text-xs mb-2">
            Example configuration output:
          </p>
          <pre className="text-xs text-muted-foreground whitespace-pre-wrap break-words overflow-wrap">
            {properties.length > 0
              ? properties
                  .map(({ key, value }) => `${key} = ${value}`)
                  .join('\n')
              : '# No custom properties configured'}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
}
