import { ChevronLeft, ChevronRight } from 'lucide-react';
import { IconButton } from '../../ui/Button';
import { number } from '../../../utils/format';

export interface PaginationControlProps {
  page: number;
  pageCount: number;
  pageSize: number;
  totalItems: number;
  itemLabel: string;
  onPageChange: (page: number) => void;
}

export function PaginationControl({
  page,
  pageCount,
  pageSize,
  totalItems,
  itemLabel,
  onPageChange,
}: PaginationControlProps) {
  const firstItem = totalItems ? (page - 1) * pageSize + 1 : 0;
  const lastItem = Math.min(page * pageSize, totalItems);

  return (
    <nav className="pagination-control" aria-label={`${itemLabel} pagination`}>
      <span className="pagination-summary">
        {number(firstItem)}-{number(lastItem)} of {number(totalItems)} {itemLabel}
      </span>
      <span className="pagination-page">Page {number(page)} of {number(pageCount)}</span>
      <span className="pagination-actions">
        <IconButton
          label="Previous page"
          icon={ChevronLeft}
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        />
        <IconButton
          label="Next page"
          icon={ChevronRight}
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
        />
      </span>
    </nav>
  );
}
