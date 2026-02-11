import { sortItems, toggleSortDirection } from '../sorting';

describe('Sorting Utilities', () => {
  describe('sortItems', () => {
    const mockItems = [
      { id: '1', name: 'Charlie', created_at: '2023-01-03' },
      { id: '2', name: 'Alice', created_at: '2023-01-01' },
      { id: '3', name: 'Bob', created_at: '2023-01-02' },
      { id: '4', name: null, created_at: undefined },
    ];

    it('should sort items by name in ascending order', () => {
      const result = sortItems(mockItems, 'name', 'asc');
      expect(result.map((item) => item.name)).toEqual([
        null,
        'Alice',
        'Bob',
        'Charlie',
      ]);
    });

    it('should sort items by name in descending order', () => {
      const result = sortItems(mockItems, 'name', 'desc');
      expect(result.map((item) => item.name)).toEqual([
        'Charlie',
        'Bob',
        'Alice',
        null,
      ]);
    });

    it('should sort items by created_at in ascending order', () => {
      const result = sortItems(mockItems, 'created_at', 'asc');
      expect(result.map((item) => item.created_at)).toEqual([
        undefined,
        '2023-01-01',
        '2023-01-02',
        '2023-01-03',
      ]);
    });

    it('should handle empty array', () => {
      const result = sortItems([], 'name', 'asc');
      expect(result).toEqual([]);
    });

    it('should handle mixed data types', () => {
      const mixedItems = [
        { id: '1', count: 3 },
        { id: '2', count: 1 },
        { id: '3', count: 2 },
      ];
      const result = sortItems(mixedItems, 'count', 'asc');
      expect(result.map((item) => item.count)).toEqual([1, 2, 3]);
    });
  });

  describe('toggleSortDirection', () => {
    it('should toggle from asc to desc', () => {
      expect(toggleSortDirection('asc')).toBe('desc');
    });

    it('should toggle from desc to asc', () => {
      expect(toggleSortDirection('desc')).toBe('asc');
    });
  });
});
