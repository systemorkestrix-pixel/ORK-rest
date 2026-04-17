import { api } from '@/shared/api/client';
import type { Product, ProductCategory, ProductPayload, ProductsPage, UserRole } from '@/shared/api/types';

export interface ProductsPagedParams {
  page: number;
  pageSize: number;
  search?: string;
  sortBy?: 'id' | 'name' | 'category' | 'price' | 'available';
  sortDirection?: 'asc' | 'desc';
  archiveState?: 'all' | 'active' | 'archived';
  kind?: 'all' | 'primary' | 'secondary';
}

export interface ProductCategoryPayload {
  name: string;
  active: boolean;
  sort_order: number;
}

export interface ProductImagePayload {
  mime_type: string;
  data_base64: string;
}

const managerRole = (role?: UserRole) => role ?? 'manager';

export const productApi = {
  getManagerProducts: (role?: UserRole, kind: 'all' | 'primary' | 'secondary' = 'all'): Promise<Product[]> =>
    api.managerProducts(managerRole(role), kind),
  getManagerProductsPaged: (role: UserRole | undefined, params: ProductsPagedParams): Promise<ProductsPage> =>
    api.managerProductsPaged(managerRole(role), params),
  getCategories: (role?: UserRole): Promise<ProductCategory[]> => api.managerCategories(managerRole(role)),
  createCategory: (role: UserRole | undefined, payload: ProductCategoryPayload): Promise<ProductCategory> =>
    api.managerCreateCategory(managerRole(role), payload),
  updateCategory: (
    role: UserRole | undefined,
    categoryId: number,
    payload: ProductCategoryPayload
  ): Promise<ProductCategory> => api.managerUpdateCategory(managerRole(role), categoryId, payload),
  deleteCategory: (role: UserRole | undefined, categoryId: number): Promise<void> =>
    api.managerDeleteCategory(managerRole(role), categoryId),
  createProduct: (role: UserRole | undefined, payload: ProductPayload): Promise<Product> =>
    api.managerCreateProduct(managerRole(role), payload),
  updateProduct: (role: UserRole | undefined, productId: number, payload: ProductPayload): Promise<Product> =>
    api.managerUpdateProduct(managerRole(role), productId, payload),
  deleteProduct: (role: UserRole | undefined, productId: number): Promise<void> =>
    api.managerDeleteProduct(managerRole(role), productId),
  deleteProductPermanently: (role: UserRole | undefined, productId: number): Promise<void> =>
    api.managerDeleteProductPermanently(managerRole(role), productId),
  uploadProductImage: (role: UserRole | undefined, productId: number, payload: ProductImagePayload): Promise<Product> =>
    api.managerUploadProductImage(managerRole(role), productId, payload),
};
