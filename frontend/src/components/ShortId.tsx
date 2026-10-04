import './shortid.css';

/** `req_1b6d959edffd4e4e807ea8bc08bc8acd` → `req_…bc8acd`. Short ids pass through. */
export function shortId(id: string, tail = 6): string {
  if (id.length <= tail + 6) return id;
  const cut = id.indexOf('_');
  return `${cut > 0 && cut < 6 ? id.slice(0, cut + 1) : ''}…${id.slice(-tail)}`;
}

/**
 * Small chip for a raw id: sighted users see the short form (full id on hover via `title`); the full id stays in the text
 * for assistive tech, copy/search and text assertions, so it is still findable while it no longer takes a title's place.
 */
export function ShortId({ id }: { id: string }) {
  return <code className="short-id" title={id}><span aria-hidden="true">{shortId(id)}</span><span className="short-id-full">{id}</span></code>;
}
