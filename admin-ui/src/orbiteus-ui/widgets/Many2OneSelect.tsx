"use client";

import { Select, type SelectProps } from "@mantine/core";
import axios from "axios";
import { useEffect, useState } from "react";

/**
 * Many2One widget. Resolves the related record's display name on demand.
 *
 * Strategy: GET /api/<module>/<model>?name__contains=<query>&limit=20
 * The backend returns `{ items: [...] }`. Items must expose `id` and `name`.
 */
interface Props extends Omit<SelectProps, "data" | "onChange" | "value"> {
  relation: string;            // e.g. "crm.team"
  value: string | null;        // current id
  onChange: (id: string | null) => void;
  initialLabel?: string;       // resolved display name from `<field>__name`
  placeholder?: string;
}

function relationToPath(relation: string): string {
  // "crm.team" → "/api/crm/team"
  const [mod, ...rest] = relation.split(".");
  return `/api/${mod}/${rest.join(".").replace(/\./g, "-")}`;
}

export function Many2OneSelect({
  relation,
  value,
  onChange,
  initialLabel,
  placeholder = "Select…",
  ...rest
}: Props) {
  const [search, setSearch] = useState("");
  const [data, setData] = useState<{ value: string; label: string }[]>([]);

  useEffect(() => {
    if (initialLabel && value && !data.some((d) => d.value === value)) {
      setData((prev) => [...prev, { value, label: initialLabel }]);
    }
  }, [initialLabel, value, data]);

  useEffect(() => {
    let cancelled = false;
    const path = relationToPath(relation);
    axios
      .get(path, { params: { name__contains: search, limit: 20 } })
      .then((res) => {
        if (cancelled) return;
        const items = (res.data?.items ?? []).map((it: { id: string; name: string }) => ({
          value: it.id,
          label: it.name ?? "(no name)",
        }));
        setData(items);
      })
      .catch(() => {
        /* swallow — empty list is acceptable */
      });
    return () => {
      cancelled = true;
    };
  }, [relation, search]);

  return (
    <Select
      searchable
      clearable
      placeholder={placeholder}
      data={data}
      value={value}
      onChange={(v) => onChange(v ?? null)}
      onSearchChange={setSearch}
      {...rest}
    />
  );
}
