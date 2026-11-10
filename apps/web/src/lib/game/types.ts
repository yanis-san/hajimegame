import type { ClientMessage, SetSettings } from '@hajime/protocol';

/** Omit that distributes over a union (the built-in one collapses it to the common keys). */
type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never;

/** What the app sends: any client message without the protocol version, which the client adds. */
export type Outgoing = DistributiveOmit<ClientMessage, 'v'>;

/** The editable part of a `settings` message (everything except the tag and version). */
export type SetSettingsPatch = Partial<Omit<SetSettings, 't' | 'v'>>;
