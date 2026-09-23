"use client";

import { RuleCard } from "@/components/app/rule-card";
import { useGuild } from "@/components/app/guild-shell";
import { ErrorState, PageLoading, PageTitle } from "@/components/app/ui";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";

export default function RulesPage() {
  const { guild, refreshGuild } = useGuild();
  const rules = useApi(() => api.rules(guild.id), `rules-${guild.id}`);

  if (rules.loading) return <PageLoading />;
  if (rules.error || !rules.data) return <ErrorState message={rules.error ?? "Couldn't load rules."} onRetry={rules.reload} />;
  const enabled = rules.data.filter((r) => r.enabled).length;

  return (
    <>
      <PageTitle
        title="Protection rules"
        description={`${enabled} of ${rules.data.length} modules enabled. Each detection is logged; the actions below decide what else happens. Bans are never automatic.`}
      />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-3">
        {rules.data.map((rule) => (
          <RuleCard
            key={rule.module}
            guildId={guild.id}
            rule={rule}
            hasAlertChannel={Boolean(guild.alert_channel_id)}
            hasRestrictedRole={Boolean(guild.restricted_role_id)}
            onSaved={(updated) => {
              rules.mutate((current) => current.map((r) => (r.module === updated.module ? updated : r)));
              refreshGuild();
            }}
          />
        ))}
      </div>
    </>
  );
}
