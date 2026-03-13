"use client";

import { useEffect, useRef } from "react";

const DEFAULT_MESSAGE = "저장하지 않은 변경 사항이 있습니다. 페이지를 이동하면 변경 내용이 사라질 수 있습니다. 이동하시겠습니까?";

export function useUnsavedChangesGuard(
  enabled: boolean,
  message: string = DEFAULT_MESSAGE
) {
  const enabledRef = useRef(enabled);
  const messageRef = useRef(message);
  const ignoreNextPopstateRef = useRef(false);

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  useEffect(() => {
    messageRef.current = message;
  }, [message]);

  useEffect(() => {
    function handlePopState() {
      if (ignoreNextPopstateRef.current) {
        ignoreNextPopstateRef.current = false;
        return;
      }
      if (!enabledRef.current) {
        return;
      }

      if (window.confirm(messageRef.current)) {
        return;
      }

      ignoreNextPopstateRef.current = true;
      window.history.go(1);
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    function handleBeforeUnload(event: BeforeUnloadEvent) {
      if (!enabledRef.current) {
        return;
      }
      event.preventDefault();
      event.returnValue = messageRef.current;
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);

  useEffect(() => {
    function handleDocumentClick(event: MouseEvent) {
      if (!enabledRef.current) {
        return;
      }
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }

      const anchor = target.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) {
        return;
      }
      if (anchor.target && anchor.target !== "_self") {
        return;
      }

      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("javascript:")) {
        return;
      }

      const nextUrl = new URL(anchor.href, window.location.href);
      const currentUrl = new URL(window.location.href);
      if (nextUrl.href === currentUrl.href) {
        return;
      }

      if (!window.confirm(messageRef.current)) {
        event.preventDefault();
        event.stopPropagation();
      }
    }

    document.addEventListener("click", handleDocumentClick, true);
    return () => document.removeEventListener("click", handleDocumentClick, true);
  }, []);
}
