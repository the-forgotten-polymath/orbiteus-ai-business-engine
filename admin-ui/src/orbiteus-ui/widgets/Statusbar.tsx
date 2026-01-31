"use client";

import { Group, Stepper } from "@mantine/core";
import { useMemo } from "react";

export interface StatusbarStep {
  id: string;
  label: string;
  is_won?: boolean;
  is_lost?: boolean;
}

interface Props {
  steps: StatusbarStep[];
  currentId: string | null;
  onChange?: (stepId: string) => void;
  readOnly?: boolean;
}

export function Statusbar({ steps, currentId, onChange, readOnly }: Props) {
  const activeIndex = useMemo(
    () => steps.findIndex((s) => s.id === currentId),
    [steps, currentId],
  );
  return (
    <Group gap="xs" wrap="nowrap">
      <Stepper
        active={activeIndex < 0 ? 0 : activeIndex}
        onStepClick={readOnly ? undefined : (i) => onChange?.(steps[i].id)}
        size="sm"
        styles={{ stepBody: { display: "block" } }}
      >
        {steps.map((s) => (
          <Stepper.Step
            key={s.id}
            label={s.label}
            color={s.is_won ? "green" : s.is_lost ? "red" : undefined}
          />
        ))}
      </Stepper>
    </Group>
  );
}
