// Public reference amounts only. Future checkout must obtain versioned prices from the backend.
export const publicPlans = [
  {
    code: 'initial',
    name: 'Inicial',
    price: 4500,
    cabins: 3,
    users: 2,
    description: 'Para empezar a ordenar tu alojamiento.',
  },
  {
    code: 'growth',
    name: 'Crecimiento',
    price: 9900,
    cabins: 8,
    users: 5,
    description: 'Más espacio para tu operación y tu equipo.',
  },
  {
    code: 'operator',
    name: 'Operador',
    price: 19900,
    cabins: 20,
    users: 10,
    description: 'Una vista clara de un negocio más grande.',
  },
] as const

export function referenceMonthlyPrice(code: string) {
  const plan = publicPlans.find((item) => item.code === code)
  return plan
    ? `$${plan.price.toLocaleString('es-CL')} CLP/mes · Referencia de simulación`
    : 'Precio de referencia no disponible'
}
