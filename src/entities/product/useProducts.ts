import { useQuery } from '@tanstack/react-query';

import type { UserRole } from '@/shared/api/types';
import type { Product, ProductCategory, ProductsPage } from './product.types';
import { productApi, type ProductsPagedParams } from './product.api';

export function useManagerProducts(role: UserRole | undefined, kind: 'all' | 'primary' | 'secondary' = 'all', enabled = true) {
  return useQuery<Product[]>({
    queryKey: ['manager-products', kind],
    queryFn: () => productApi.getManagerProducts(role, kind),
    enabled,
  });
}

export function useManagerProductsPaged(role: UserRole | undefined, params: ProductsPagedParams, enabled = true) {
  return useQuery<ProductsPage>({
    queryKey: [
      'manager-products-paged',
      params.page,
      params.search ?? '',
      params.sortBy ?? 'id',
      params.sortDirection ?? 'desc',
      params.archiveState ?? 'all',
      params.kind ?? 'all',
    ],
    queryFn: () => productApi.getManagerProductsPaged(role, params),
    enabled,
  });
}

export function useManagerCategories(role: UserRole | undefined, enabled = true) {
  return useQuery<ProductCategory[]>({
    queryKey: ['manager-product-categories'],
    queryFn: () => productApi.getCategories(role),
    enabled,
  });
}
