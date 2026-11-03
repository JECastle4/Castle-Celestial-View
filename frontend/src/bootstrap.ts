export async function mountWhenReady(
  ready: Promise<unknown>,
  mount: () => void,
  reportError: (error: unknown) => void,
) {
  try {
    await ready
    mount()
  } catch (error) {
    reportError(error)
  }
}
