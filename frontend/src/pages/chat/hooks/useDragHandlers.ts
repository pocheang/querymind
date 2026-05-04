import { useEffect } from "react";

type DragHandlers = {
  onComposerDragEnter: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDragOver: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDragLeave: (evt: React.DragEvent<HTMLElement>) => void;
};

export function useDragHandlers(setComposerDropActive: (active: boolean) => void): DragHandlers {
  useEffect(() => {
    const preventDefault = (evt: DragEvent) => evt.preventDefault();
    window.addEventListener("dragover", preventDefault);
    window.addEventListener("drop", preventDefault);
    return () => {
      window.removeEventListener("dragover", preventDefault);
      window.removeEventListener("drop", preventDefault);
    };
  }, []);

  return {
    onComposerDragEnter: (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      setComposerDropActive(true);
    },
    onComposerDragOver: (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      setComposerDropActive(true);
    },
    onComposerDragLeave: (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      setComposerDropActive(false);
    },
  };
}
