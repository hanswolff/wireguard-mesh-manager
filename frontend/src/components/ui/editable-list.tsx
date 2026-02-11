'use client';

import { useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Plus, Trash2, Edit2, Check, X } from 'lucide-react';
import { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface EditableListProps {
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
  label?: string;
  description?: string | ReactNode;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  Icon?: LucideIcon;
  disabled?: boolean;
}

export function EditableList({
  items,
  onChange,
  placeholder = 'https://example.com',
  label = 'Items',
  description,
  emptyStateTitle = 'No items configured',
  emptyStateDescription = 'Add an item to get started',
  Icon,
  disabled = false,
}: EditableListProps) {
  const [localItems, setLocalItems] = useState(items);
  const [newItem, setNewItem] = useState('');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    setLocalItems(items);
  }, [items]);

  const addItem = () => {
    const trimmed = newItem.trim();
    if (trimmed && !localItems.includes(trimmed)) {
      const updated = [...localItems, trimmed];
      setLocalItems(updated);
      onChange(updated);
      setNewItem('');
    }
  };

  const removeItem = (index: number) => {
    const updated = localItems.filter((_, i) => i !== index);
    setLocalItems(updated);
    onChange(updated);
  };

  const startEdit = (index: number) => {
    setEditingIndex(index);
    setEditValue(localItems[index] ?? '');
  };

  const saveEdit = () => {
    const trimmed = editValue.trim();
    if (editingIndex !== null && trimmed) {
      const updated = [...localItems];
      updated[editingIndex] = trimmed;
      setLocalItems(updated);
      onChange(updated);
      setEditingIndex(null);
      setEditValue('');
    }
  };

  const cancelEdit = () => {
    setEditingIndex(null);
    setEditValue('');
  };

  return (
    <div className="space-y-4">
      {/* Add New Item */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          {Icon && (
            <Icon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          )}
          <Input
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            placeholder={placeholder}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addItem();
              }
            }}
            disabled={disabled}
            className={Icon ? 'pl-9' : ''}
          />
        </div>
        <Button
          onClick={addItem}
          disabled={disabled || !newItem.trim() || items.includes(newItem.trim())}
          size="icon"
          aria-label={`Add ${label}`}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Items List */}
      {localItems.length > 0 ? (
        <div className="space-y-2">
          <Label className="text-sm font-medium">{label}</Label>
          <div className="space-y-2">
            {localItems.map((item, index) => (
              <div
                key={index}
                className="flex items-center gap-2 group p-2 border rounded-lg hover:bg-muted/50 transition-colors"
              >
                {editingIndex === index ? (
                  <>
                    <div className="flex-1 relative">
                      {Icon && (
                        <Icon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      )}
                      <Input
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            saveEdit();
                          } else if (e.key === 'Escape') {
                            e.preventDefault();
                            cancelEdit();
                          }
                        }}
                        disabled={disabled}
                        className={Icon ? 'pl-9' : ''}
                        autoFocus
                      />
                    </div>
                    <Button
                      onClick={saveEdit}
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      disabled={disabled}
                      aria-label="Check"
                    >
                      <Check className="h-4 w-4 text-green-600" />
                    </Button>
                    <Button
                      onClick={cancelEdit}
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8"
                      disabled={disabled}
                      aria-label="Cancel"
                    >
                      <X className="h-4 w-4 text-red-600" />
                    </Button>
                  </>
                ) : (
                  <>
                    {Icon && (
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    )}
                    <span className="flex-1 font-mono text-sm">{item}</span>
                    <Button
                      onClick={() => startEdit(index)}
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                      disabled={disabled}
                      aria-label={`Edit ${item}`}
                    >
                      <Edit2 className="h-3 w-3" />
                    </Button>
                    <Button
                      onClick={() => removeItem(index)}
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity hover:text-destructive"
                      disabled={disabled}
                      aria-label={`Remove ${item}`}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          {Icon && (
            <Icon className="h-12 w-12 mx-auto mb-3 opacity-20" />
          )}
          <p className="text-sm">{emptyStateTitle}</p>
          <p className="text-xs mt-1">{emptyStateDescription}</p>
        </div>
      )}

      {/* Description */}
      {description && (
        <div className="p-3 bg-muted/50 rounded-md">
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      )}
    </div>
  );
}
