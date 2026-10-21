export function useTimeZones(currentTimeZone = ""): string[] {
  const timeZones = new Set(["UTC", ...Intl.supportedValuesOf("timeZone")])

  if (currentTimeZone) {
    timeZones.add(currentTimeZone)
  }

  return ["UTC", ...Array.from(timeZones).filter((timeZone) => timeZone !== "UTC").sort()]
}
