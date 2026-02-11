export type SortDirection = 'asc' | 'desc';

export function sortItems<T extends Record<string, unknown>>(
  items: T[],
  field: keyof T,
  direction: SortDirection = 'asc'
): T[] {
  return [...items].sort((a, b) => {
    let aValue: unknown = a[field];
    let bValue: unknown = b[field];

    if (aValue === null || aValue === undefined) aValue = '';
    if (bValue === null || bValue === undefined) bValue = '';

    if (typeof aValue === 'string' && typeof bValue === 'string') {
      aValue = aValue.toLowerCase();
      bValue = bValue.toLowerCase();
    }

    const aStr = String(aValue);
    const bStr = String(bValue);

    if (direction === 'asc') {
      return aStr > bStr ? 1 : aStr < bStr ? -1 : 0;
    } else {
      return aStr < bStr ? 1 : aStr > bStr ? -1 : 0;
    }
  });
}

export function toggleSortDirection(current: SortDirection): SortDirection {
  return current === 'asc' ? 'desc' : 'asc';
}
