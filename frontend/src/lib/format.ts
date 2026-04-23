const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
})

const date = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'short',
  day: '2-digit',
})

export function formatMoney(value: number): string {
  return money.format(value)
}

export function formatDate(iso: string): string {
  return date.format(new Date(`${iso}T00:00:00`))
}
