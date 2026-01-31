"use client";

/**
 * MonetaryField — single source of truth for rendering monetary values.
 *
 * Two consumers:
 *   - `MonetaryCell`   — read-only display for `ResourceList` cells
 *                        (and any future Kanban / Calendar card).
 *   - `MonetaryInput`  — form input for `ResourceForm`. Wraps Mantine's
 *                        `NumberInput` so the currency code shows up as
 *                        the suffix and decimals are formatted.
 *
 * The currency code arrives via the `currency_code` field on
 * `FieldMeta` (`/api/base/ui-config`). When absent we fall back to
 * "PLN" so the UI keeps working against older backends.
 */
import { NumberInput } from "@mantine/core";
import { useMemo } from "react";

const DEFAULT_CURRENCY = "PLN";

export interface MonetaryCellProps {
  value: unknown;
  currencyCode?: string;
  /** Used as fallback when value is null/empty. Defaults to em-dash. */
  emptyPlaceholder?: string;
}

/** Read-only formatted value, used in tables. */
export function MonetaryCell({
  value, currencyCode, emptyPlaceholder = "—",
}: MonetaryCellProps): string {
  if (value == null || value === "") return emptyPlaceholder;
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  const code = (currencyCode && currencyCode.trim()) || DEFAULT_CURRENCY;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency", currency: code,
      // Always show two decimals so "65000" reads as "65,000.00 PLN"
      // rather than "65,000 PLN" — matches the convention people expect
      // on invoices and quotes.
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    // Unknown ISO-4217 code — render the number + raw code as suffix.
    return `${new Intl.NumberFormat(undefined, {
      minimumFractionDigits: 2, maximumFractionDigits: 2,
    }).format(n)} ${code}`;
  }
}

export interface MonetaryInputProps {
  label: string;
  value: number | "" | undefined;
  onChange: (value: number | "" | undefined) => void;
  required?: boolean;
  disabled?: boolean;
  currencyCode?: string;
  /** Optional helper / error text under the input. */
  description?: string;
  error?: string | null;
  placeholder?: string;
}

/** Form input — `NumberInput` with currency suffix. */
export function MonetaryInput({
  label, value, onChange, required, disabled,
  currencyCode, description, error, placeholder,
}: MonetaryInputProps) {
  const code = (currencyCode && currencyCode.trim()) || DEFAULT_CURRENCY;
  // Memoise the suffix string so React doesn't tear the component
  // tree on every parent re-render with a fresh string identity.
  const suffix = useMemo(() => ` ${code}`, [code]);

  return (
    <NumberInput
      label={label}
      description={description}
      error={error || undefined}
      value={value === undefined ? "" : value}
      onChange={(v) => {
        if (typeof v === "number") onChange(v);
        else if (v === "" || v === undefined) onChange("");
        else {
          const n = Number(v);
          onChange(Number.isNaN(n) ? "" : n);
        }
      }}
      required={required}
      disabled={disabled}
      decimalScale={2}
      thousandSeparator=" "
      suffix={suffix}
      placeholder={placeholder}
      hideControls
    />
  );
}
