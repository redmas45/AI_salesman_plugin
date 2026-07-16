import { useEffect, useState } from 'react';

export interface PaginationState<T> {
  page: number;
  pageCount: number;
  pageItems: T[];
  setPage: (page: number) => void;
}

export function usePagination<T>(items: T[], pageSize: number, resetKey = ''): PaginationState<T> {
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const visiblePage = Math.min(page, pageCount);
  const start = (visiblePage - 1) * pageSize;

  useEffect(() => {
    setPage(1);
  }, [resetKey]);

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  return {
    page: visiblePage,
    pageCount,
    pageItems: items.slice(start, start + pageSize),
    setPage,
  };
}
