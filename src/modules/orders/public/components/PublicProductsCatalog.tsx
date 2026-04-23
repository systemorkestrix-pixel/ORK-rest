import { Minus, Plus } from 'lucide-react';

import type { PublicJourneyProduct } from '@/shared/api/types';
import type { CartRow } from '../publicOrder.helpers';
import { resolveImageUrl } from '../publicOrder.helpers';

interface PublicProductsCatalogProps {
  productsLoading: boolean;
  productsErrorText: string;
  totalProducts: number;
  categoryEntries: Array<[string, PublicJourneyProduct[]]>;
  cart: Record<number, CartRow>;
  onIncreaseQuantity: (product: PublicJourneyProduct) => void;
  onDecreaseQuantity: (product: PublicJourneyProduct) => void;
}

export function PublicProductsCatalog({
  productsLoading,
  productsErrorText,
  totalProducts,
  categoryEntries,
  cart,
  onIncreaseQuantity,
  onDecreaseQuantity,
}: PublicProductsCatalogProps) {
  return (
    <section className="rounded-[34px] border border-[#eadbc7] bg-[#fffaf3] p-4 shadow-[0_24px_60px_rgba(170,126,70,0.12)] md:p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-black text-[#2d2117]">قائمة الطلب</h3>
          <p className="mt-1 text-sm font-semibold text-[#7c6651]">أضف الكمية مباشرة من البطاقات ثم افتح الطلب للمراجعة النهائية.</p>
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
                const quantity = cart[product.id]?.quantity ?? 0;
                const imageUrl = resolveImageUrl(product.image_path);

                return (
                  <article
                    key={product.id}
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
                    </div>

                    <div className="flex flex-1 flex-col justify-between p-4">
                      <div className="space-y-2">
                        <h5 className="line-clamp-2 min-h-[48px] text-sm font-black leading-6 text-[#2d2117] md:text-base">
                          {product.name}
                        </h5>
                        {product.description ? (
                          <p className="line-clamp-2 text-[11px] font-semibold leading-5 text-[#8b735d]">{product.description}</p>
                        ) : (
                          <p className="text-[11px] font-semibold text-[#8b735d]">جاهز للإضافة المباشرة</p>
                        )}
                      </div>

                      <div className="mt-4 flex items-center justify-between gap-3 rounded-2xl border border-[#eadbc7] bg-[#fff8ee] p-2">
                        <button
                          type="button"
                          onClick={() => onDecreaseQuantity(product)}
                          disabled={quantity === 0}
                          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#eadbc7] bg-white text-[#5c4735] transition hover:bg-[#fff2df] disabled:cursor-not-allowed disabled:opacity-45"
                          aria-label={`تقليل كمية ${product.name}`}
                        >
                          <Minus className="h-4 w-4" />
                        </button>

                        <div className="min-w-[64px] text-center">
                          <p className="text-[11px] font-bold text-[#8b735d]">في الطلب</p>
                          <p className="text-xl font-black text-[#2d2117]">{quantity}</p>
                        </div>

                        <button
                          type="button"
                          onClick={() => onIncreaseQuantity(product)}
                          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-[#e38b38] text-[#1a120d] transition hover:bg-[#ef9a4b]"
                          aria-label={`زيادة كمية ${product.name}`}
                        >
                          <Plus className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
