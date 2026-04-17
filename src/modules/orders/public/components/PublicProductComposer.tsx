import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, CheckCircle2, Minus, Plus, Trash2, X } from 'lucide-react';

import type { PublicJourneyProduct } from '@/shared/api/types';
import { type CartRow, getCartRowTotal, resolveImageUrl } from '../publicOrder.helpers';

interface PublicProductComposerProps {
  open: boolean;
  product: PublicJourneyProduct | null;
  existingRow?: CartRow;
  onClose: () => void;
  onSave: (row: CartRow | null) => void;
}

type ComposerStep = 'quantity' | 'review';

export function PublicProductComposer({
  open,
  product,
  existingRow,
  onClose,
  onSave,
}: PublicProductComposerProps) {
  const [quantity, setQuantity] = useState(1);
  const [step, setStep] = useState<ComposerStep>('quantity');

  useEffect(() => {
    if (!open || !product) {
      return;
    }
    setStep('quantity');
    setQuantity(existingRow?.quantity ?? 1);
  }, [existingRow, open, product]);

  const imageUrl = product ? resolveImageUrl(product.image_path) : null;

  const previewRow = useMemo<CartRow | null>(() => {
    if (!product) {
      return null;
    }
    return { product, quantity };
  }, [product, quantity]);

  const total = previewRow ? getCartRowTotal(previewRow) : 0;

  const handleSave = () => {
    if (!product || quantity <= 0) {
      onSave(null);
      return;
    }
    onSave({ product, quantity });
  };

  if (!open || !product) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 bg-[#6d5845]/20 backdrop-blur-[2px]" dir="rtl">
      <div className="absolute inset-x-0 bottom-0 top-0 overflow-y-auto md:inset-0 md:flex md:items-center md:justify-center md:p-4">
        <div className="min-h-full w-full rounded-none border-0 bg-[#fffaf3] shadow-none md:min-h-0 md:max-h-[92vh] md:max-w-3xl md:overflow-hidden md:rounded-[34px] md:border md:border-[#eadbc7] md:shadow-[0_28px_90px_rgba(170,126,70,0.20)]">
          <div className="sticky top-0 z-10 border-b border-[#eadbc7] bg-[#fffaf3]/95 px-4 py-4 backdrop-blur md:px-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-black tracking-[0.18em] text-[#8b735d]">PRODUCT</p>
                <h3 className="mt-2 text-2xl font-black text-[#2d2117]">{product.name}</h3>
                <p className="mt-1 text-sm font-semibold text-[#6f5b49]">حدد الكمية ثم راجع الإضافة.</p>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#eadbc7] bg-white text-[#5c4735] transition hover:bg-[#fff2df]"
                aria-label="إغلاق"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 grid gap-2 md:grid-cols-2">
              {[
                { id: 'quantity' as const, label: '1. الكمية' },
                { id: 'review' as const, label: '2. المراجعة' },
              ].map((stepCard) => {
                const isCurrent = stepCard.id === step;
                const isDone = stepCard.id === 'quantity' && step === 'review';
                return (
                  <div
                    key={stepCard.id}
                    className={[
                      'rounded-2xl border px-4 py-3 text-sm font-black transition',
                      isCurrent
                        ? 'border-[#e38b38] bg-[#fff2df] text-[#8f5126]'
                        : isDone
                          ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                          : 'border-[#eadbc7] bg-white text-[#8b735d]',
                    ].join(' ')}
                  >
                    {stepCard.label}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-5 p-4 md:max-h-[calc(92vh-210px)] md:overflow-y-auto md:p-6">
            <section className="grid gap-4 rounded-[28px] border border-[#eadbc7] bg-white p-4 md:grid-cols-[220px_minmax(0,1fr)]">
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt={product.name}
                  className="aspect-square w-full rounded-3xl border border-[#f0e2cf] object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="flex aspect-square items-center justify-center rounded-3xl border border-dashed border-[#eadbc7] bg-[#fffaf3] text-sm font-bold text-[#8b735d]">
                  {product.name}
                </div>
              )}

              <div className="space-y-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-2">
                    <p className="text-lg font-black text-[#2d2117]">{product.name}</p>
                    {product.description ? (
                      <p className="text-sm leading-7 text-[#6f5b49]">{product.description}</p>
                    ) : null}
                  </div>
                  <span className="rounded-full border border-[#f0d4ae] bg-[#fff3df] px-3 py-1 text-xs font-black text-[#a05e24]">
                    {product.price.toFixed(2)} د.ج
                  </span>
                </div>

                {step === 'quantity' ? (
                  <div className="rounded-3xl border border-[#eadbc7] bg-[#fffaf3] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-black text-[#2d2117]">الكمية</p>
                        <p className="mt-1 text-xs font-semibold text-[#7c6651]">اضبطها الآن ثم تابع.</p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setQuantity((current) => Math.max(0, current - 1))}
                          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[#eadbc7] bg-white text-[#4a382a] transition hover:bg-[#fff2df]"
                          aria-label={`تقليل كمية ${product.name}`}
                        >
                          <Minus className="h-4 w-4" />
                        </button>
                        <span className="min-w-12 text-center text-xl font-black text-[#2d2117]">{quantity}</span>
                        <button
                          type="button"
                          onClick={() => setQuantity((current) => current + 1)}
                          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-[#e38b38] text-[#1a120d] transition hover:bg-[#ef9a4b]"
                          aria-label={`زيادة كمية ${product.name}`}
                        >
                          <Plus className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {quantity === 0 ? (
                      <p className="mt-3 text-xs font-semibold text-rose-700">سيتم حذف المنتج من الطلب عند الحفظ.</p>
                    ) : null}
                  </div>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-3">
                    <ComposerInfoCard label="المنتج" value={product.name} />
                    <ComposerInfoCard label="الكمية" value={quantity} />
                    <ComposerInfoCard label="الإجمالي" value={`${total.toFixed(2)} د.ج`} />
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="sticky bottom-0 border-t border-[#eadbc7] bg-[#fffaf3]/95 px-4 py-4 backdrop-blur md:px-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="text-sm font-black text-[#2d2117]">الإجمالي الحالي: {total.toFixed(2)} د.ج</div>

              {step === 'quantity' ? (
                <div className="grid gap-2 md:grid-cols-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-2xl border border-[#eadbc7] bg-white px-4 text-sm font-black text-[#5c4735] transition hover:bg-[#fff2df]"
                  >
                    <ArrowRight className="h-4 w-4" />
                    <span>إغلاق</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep('review')}
                    className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-2xl bg-[#e38b38] px-5 text-sm font-black text-[#1a120d] transition hover:bg-[#ef9a4b]"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    <span>متابعة</span>
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-2 md:flex-row">
                  <button
                    type="button"
                    onClick={() => setStep('quantity')}
                    className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-2xl border border-[#eadbc7] bg-white px-4 text-sm font-black text-[#5c4735] transition hover:bg-[#fff2df]"
                  >
                    <ArrowRight className="h-4 w-4" />
                    <span>عودة</span>
                  </button>

                  {existingRow ? (
                    <button
                      type="button"
                      onClick={() => onSave(null)}
                      className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-2xl border border-rose-300 bg-rose-50 px-4 text-sm font-black text-rose-700 transition hover:bg-rose-100"
                    >
                      <Trash2 className="h-4 w-4" />
                      <span>حذف</span>
                    </button>
                  ) : null}

                  <button
                    type="button"
                    onClick={handleSave}
                    className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-2xl bg-[#e38b38] px-5 text-sm font-black text-[#1a120d] transition hover:bg-[#ef9a4b]"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    <span>{existingRow ? 'تحديث الطلب' : 'إضافة إلى الطلب'}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ComposerInfoCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-[#eadbc7] bg-[#fffaf3] p-3">
      <p className="text-[11px] font-bold text-[#7c6651]">{label}</p>
      <p className="mt-2 text-sm font-black text-[#2d2117]">{value}</p>
    </div>
  );
}
