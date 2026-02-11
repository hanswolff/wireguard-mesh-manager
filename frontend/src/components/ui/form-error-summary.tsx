interface FormErrorSummaryProps {
  messages: string[];
  title?: string;
  className?: string;
}

export function FormErrorSummary({
  messages,
  title = 'Fix the following:',
  className,
}: FormErrorSummaryProps) {
  if (messages.length === 0) {
    return null;
  }

  return (
    <div
      className={`rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive ${className ?? ''}`.trim()}
    >
      <div className="font-semibold">{title}</div>
      <ul className="list-disc pl-5">
        {messages.map((message, index) => (
          <li key={`${message}-${index}`}>{message}</li>
        ))}
      </ul>
    </div>
  );
}
