type SystemNoticeProps = {
  title: string;
  description: string;
};

export function SystemNotice({ title, description }: SystemNoticeProps) {
  return (
    <article className="mini-card system-notice">
      <p className="eyebrow">System Notice</p>
      <h2>{title}</h2>
      <p>{description}</p>
    </article>
  );
}
