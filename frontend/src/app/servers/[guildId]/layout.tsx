import { GuildShell } from "@/components/app/guild-shell";

export default async function GuildLayout({ children, params }: LayoutProps<"/servers/[guildId]">) {
  const { guildId } = await params;
  return <GuildShell guildId={guildId}>{children}</GuildShell>;
}
