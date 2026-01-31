"use client";

/**
 * Generic empty state for list / kanban / calendar / graph views
 * (DoD §9.7).
 *
 * Behaviour:
 *   * Centred Stack with an icon, a title, an optional description,
 *     and an optional CTA button.
 *   * No tenant / module knowledge — every consumer (`ResourceList`,
 *     `ResourceKanban`, …) supplies its own copy and CTA.
 *   * Defaults to Mantine's neutral palette so the same component
 *     looks at home in every view, dark or light.
 */
import { Box, Button, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconInbox } from "@tabler/icons-react";
import Link from "next/link";
import type { ReactNode } from "react";

export interface EmptyStateProps {
  /** Headline. Defaults to "No records yet". */
  title?: string;
  /** Smaller dimmed copy under the title. */
  description?: ReactNode;
  /** Override the default IconInbox. */
  icon?: ReactNode;
  /** Primary call-to-action label. */
  ctaLabel?: string;
  /** When set, the CTA renders as a Next link to this href. */
  ctaHref?: string;
  /** When set (and ctaHref isn't), the CTA renders as a button with this onClick. */
  ctaOnClick?: () => void;
  /** Vertical padding around the block. Defaults to "xl". */
  py?: number | string;
}

export default function EmptyState({
  title = "No records yet",
  description = "Click the button below to create your first record.",
  icon,
  ctaLabel,
  ctaHref,
  ctaOnClick,
  py = "xl",
}: EmptyStateProps) {
  return (
    <Box py={py} ta="center">
      <Stack gap="sm" align="center">
        <ThemeIcon
          size={56}
          radius="xl"
          variant="light"
          color="gray"
          aria-hidden
        >
          {icon ?? <IconInbox size={28} />}
        </ThemeIcon>
        <Stack gap={4} align="center">
          <Text fw={600}>{title}</Text>
          {description ? (
            <Text size="sm" c="dimmed" maw={420}>
              {description}
            </Text>
          ) : null}
        </Stack>
        {ctaLabel ? (
          ctaHref ? (
            <Button component={Link} href={ctaHref} mt="xs">
              {ctaLabel}
            </Button>
          ) : (
            <Button mt="xs" onClick={ctaOnClick}>
              {ctaLabel}
            </Button>
          )
        ) : null}
      </Stack>
    </Box>
  );
}
