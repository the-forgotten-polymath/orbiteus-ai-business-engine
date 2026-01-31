"use client";

import { Text, type TextProps } from "@mantine/core";

interface Props extends TextProps {
  amount: number | null | undefined;
  currency?: string;
  locale?: string;
}

const FALLBACK = "—";

export function Monetary({ amount, currency = "PLN", locale, ...rest }: Props) {
  if (amount == null || Number.isNaN(amount)) {
    return <Text component="span" {...rest}>{FALLBACK}</Text>;
  }
  const formatted = new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
  return <Text component="span" {...rest}>{formatted}</Text>;
}
