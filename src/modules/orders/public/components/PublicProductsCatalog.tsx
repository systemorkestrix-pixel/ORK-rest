import { Pencil, Plus } from 'lucide-react';

import type { PublicJourneyProduct } from '@/shared/api/types';
import type { CartRow } from '../publicOrder.helpers';
import { resolveImageUrl } from '../publicOrder.helpers';

interface PublicProductsCatalogProps {
  productsLoading: boolean;
  productsErrorText: string;
  totalProducts: number;
  categoryEntries: Array<[string, PublicJourneyProduct[]]>;
  cart: Record<number, CartRow>;
  onOpenComposer: (product: PublicJourneyProduct) => void;
}

function cartQuantityLabel(quantity: number): string {
  return quantity > 0 ? `${quantity} في الطلب` : 'جاهز للإضافة';
}

export function PublicProductsCatalog({
  productsLoading,
  productsErrorText,
  totalProducts,
  categoryEntries,
  cart,
  onOpenComposer,
}: PublicProductsCatalogProps) {
  return (
    <section className="rounded-[34px] border border-[#eadbc7] bg-[#fffaf3] p-4 shadow-[0_24px_60px_rgba(170,126,70,0.12)] md:p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-black text-[#2d2117]">قائمة الطلب</h3>
          <p className="mt-1 text-sm font-semibold text-[#7c6651]">
            اختر منتجك مباشرة. التفاصيل الإضافية تظهر فقط عند فتح البطاقة.
          </p>
        </div>

        <span className="rounded-full border border-[#eadbc7] bg-white px-4 py-2 text-xs font-black text-[#6d5845]">
          الأصناف المتاحة: {totalProducts}
        </span>
      </div>

      {productsLoading ? (
        <div className="rounded-2xl border border-sky-300 bg-sky-50 p-4 text-sm font-semibold text-sky-700">
          جارٍ تحميل المنتجات...
        </div>
      ) : null}

      {productsErrorText ? (
        <div className="rounded-2xl border border-rose-300 bg-rose-50 p-4 text-sm font-semibold text-rose-700">
          {productsErrorText}
        </div>
      ) : null}

      {!productsLoading && !productsErrorText && categoryEntries.length === 0 ? (
        <div className="rounded-2xl border border-[#eadbc7] bg-white p-4 text-sm font-semibold text-[#6d5845]">
          لا توجد أصناف متاحة حاليًا.
        </div>
      ) : null}

      <div className="space-y-7">
        {categoryEntries.map(([category, products]) => (
          <section key={category} className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h4 className="text-sm font-black text-[#6d5845]">{category}</h4>
              <span className="rounded-full border border-[#eadbc7] bg-white px-3 py-1 text-[11px] font-bold text-[#8b735d]">
                {products.length} صنف
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
              {products.map((product) => {
                const cartRow = cart[product.id];
                const quantity = cartRow?.quantity ?? 0;
                const imageUrl = resolveImageUrl(product.image_path);

                return (
                  <button
                    key={product.id}
                    type="button"
                    onClick={() => onOpenComposer(product)}
                    className="group flex flex-col overflow-hidden rounded-[28px] border border-[#eadbc7] bg-white text-right shadow-[0_12px_28px_rgba(170,126,70,0.10)] transition hover:-translate-y-0.5 hover:border-[#d29d67] hover:shadow-[0_18px_36px_rgba(170,126,70,0.16)]"
                  >
                    <div className="relative aspect-square overflow-hidden bg-[#f6ead7]">
                      {imageUrl ? (
                        <img
                          src={imageUrl}
                          alt={product.name}
                          className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]"
                          loading="lazy"
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-sm font-black text-[#8b735d]">
                          {product.name}
                        </div>
                      )}

                      <span className="absolute left-3 top-3 rounded-full border border-white/60 bg-white/90 px-3 py-1 text-[11px] font-black text-[#9d5d24] shadow-sm">
                        {product.price.toFixed(2)} د.ج
                      </span>

                      {quantity > 0 ? (
                        <span className="absolute bottom-3 right-3 rounded-full bg-emerald-600 px-3 py-1 text-[11px] font-black text-white shadow-sm">
                          {quantity} ×
                        </span>
                      ) : null}
                    </div>

                    <div className="flex flex-1 flex-col justify-between p-4">
                      <div className="space-y-2">
                        <h5 className="line-clamp-2 min-h-[48px] text-sm font-black leading-6 text-[#2d2117] md:text-base">
                          {product.name}
                        </h5>
                        <p className="text-[11px] font-semibold text-[#8b735d]">{cartQuantityLabel(quantity)}</p>
                      </div>

                      <div className="mt-4 inline-flex min-h-[42px] items-center justify-center gap-2 rounded-2xl bg-[#e38b38] px-4 text-sm font-black text-[#1a120d] transition group-hover:bg-[#ef9a4b]">
                        {quantity > 0 ? <Pencil className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                        <span>{quantity > 0 ? 'تعديل' : 'إضافة'}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
