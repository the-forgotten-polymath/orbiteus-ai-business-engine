"use client";

import { TagsInput, type TagsInputProps } from "@mantine/core";

interface Props extends Omit<TagsInputProps, "value" | "onChange"> {
  value: string[];
  onChange: (next: string[]) => void;
}

export function TagsField({ value, onChange, ...rest }: Props) {
  return <TagsInput value={value ?? []} onChange={onChange} clearable {...rest} />;
}
