;;; Inline plotting support for mit-scheme-kernel.
;;;
;;; scmutils draws through X11, which is unavailable in a notebook. This file
;;; replaces the handful of graphics primitives that every scmutils plotting
;;; procedure funnels into, so a plot is *recorded as data* and handed to the
;;; kernel, which renders it with matplotlib.
;;;
;;; Because the interception happens at the primitive layer, everything above
;;; it keeps working unchanged: plot-function, plot-point, plot-line, plot-xy,
;;; plot-parametric, plot-parametric-fill, plot-circle and plot-inverse.
;;;
;;; Two things to know before editing:
;;;
;;;   * `set!`, never `define`. The REPL environment is a CHILD of the one the
;;;     compiled scmutils code is linked against, so `define` creates a fresh
;;;     binding that the compiled callers never see. `set!` mutates the binding
;;;     they do see.
;;;   * Coordinates arriving here are user coordinates, not device or frame
;;;     coordinates: plot-point-internal passes them straight through and the
;;;     X11 device is what would normally do the transform.

(define mitk:devices '())               ;every device made, newest first
(define mitk:dirty '())                 ;devices drawn on since the last emit

;;; A device is #(mitk-device xmin xmax ymin ymax ops), ops newest first.

(define (mitk:finite? x)
  (and (number? x)
       (real? x)
       (= x x)                          ;false for NaN
       (< (abs (exact->inexact x)) 1e308)))

(define (mitk:->flo x) (exact->inexact x))

(define (mitk:arg args i default)
  (if (and (> (length args) i) (number? (list-ref args i)))
      (mitk:->flo (list-ref args i))
      default))

(define (mitk:make-device xmin xmax ymin ymax)
  (let ((d (vector 'mitk-device xmin xmax ymin ymax '())))
    (set! mitk:devices (cons d mitk:devices))
    (set! mitk:dirty (cons d mitk:dirty))
    d))

(define (mitk:device? d)
  (and (vector? d)
       (= (vector-length d) 6)
       (eq? (vector-ref d 0) 'mitk-device)))

(define (mitk:ops d) (vector-ref d 5))

(define (mitk:push! d op)
  (vector-set! d 5 (cons op (mitk:ops d)))
  (if (not (memq d mitk:dirty))
      (set! mitk:dirty (cons d mitk:dirty))))

;;; ------------------------------------------------------------------ capture

(define mitk:orig-make-display-frame make-display-frame)
(define mitk:orig-graphics-draw-point graphics-draw-point)
(define mitk:orig-graphics-draw-line graphics-draw-line)
(define mitk:orig-graphics-draw-text graphics-draw-text)
(define mitk:orig-graphics-clear graphics-clear)
(define mitk:orig-graphics-close graphics-close)
(define mitk:orig-graphics-flush graphics-flush)
(define mitk:orig-graphics-device? graphics-device?)
(define mitk:orig-graphics-coordinate-limits graphics-coordinate-limits)
(define mitk:orig-graphics-device-coordinate-limits graphics-device-coordinate-limits)
(define mitk:orig-graphics-disable-buffering graphics-disable-buffering)
(define mitk:orig-graphics-enable-buffering graphics-enable-buffering)
(define mitk:orig-graphics-bind-line-style graphics-bind-line-style)
(define mitk:orig-graphics-bind-drawing-mode graphics-bind-drawing-mode)
(define mitk:orig-graphics-operation graphics-operation)
(define mitk:orig-graphics-set-coordinate-limits graphics-set-coordinate-limits)
(define mitk:orig-graphics-set-clip-rectangle graphics-set-clip-rectangle)

;;; Nominal pixel size. plot-function divides the x range by the width to pick
;;; its default step, so this sets the default sampling resolution.
(define mitk:width 800)
(define mitk:height 600)

(define (mitk:install!)
  (set! make-display-frame
        (lambda args
          (mitk:make-device (mitk:arg args 0 0.) (mitk:arg args 1 1.)
                            (mitk:arg args 2 0.) (mitk:arg args 3 1.))))
  (set! frame make-display-frame)
  (set! plot-frame make-display-frame)

  (set! graphics-draw-point
        (lambda (d x y)
          (if (mitk:device? d)
              (if (and (mitk:finite? x) (mitk:finite? y))
                  (mitk:push! d (list 'point (mitk:->flo x) (mitk:->flo y))))
              (mitk:orig-graphics-draw-point d x y))))

  (set! graphics-draw-line
        (lambda (d x0 y0 x1 y1)
          (if (mitk:device? d)
              (if (and (mitk:finite? x0) (mitk:finite? y0)
                       (mitk:finite? x1) (mitk:finite? y1))
                  (mitk:push! d (list 'line (mitk:->flo x0) (mitk:->flo y0)
                                      (mitk:->flo x1) (mitk:->flo y1))))
              (mitk:orig-graphics-draw-line d x0 y0 x1 y1))))

  (set! graphics-draw-text
        (lambda (d x y string)
          (if (mitk:device? d)
              (if (and (mitk:finite? x) (mitk:finite? y))
                  (mitk:push! d (list 'text (mitk:->flo x) (mitk:->flo y) string)))
              (mitk:orig-graphics-draw-text d x y string))))

  (set! graphics-clear
        (lambda (d)
          (if (mitk:device? d)
              (vector-set! d 5 '())
              (mitk:orig-graphics-clear d))))

  ;; Closing keeps what was drawn, so a cell that ends with graphics-close
  ;; still renders. The device simply stops being reachable as "live".
  (set! graphics-close
        (lambda (d)
          (if (mitk:device? d)
              'done
              (mitk:orig-graphics-close d))))

  (set! graphics-flush
        (lambda (d) (if (mitk:device? d) 'done (mitk:orig-graphics-flush d))))

  (set! graphics-device?
        (lambda (d) (or (mitk:device? d) (mitk:orig-graphics-device? d))))

  (set! graphics-coordinate-limits
        (lambda (d)
          (if (mitk:device? d)
              (values (vector-ref d 1) (vector-ref d 3)
                      (vector-ref d 2) (vector-ref d 4))
              (mitk:orig-graphics-coordinate-limits d))))

  ;; window-size computes (x2-x1+1, y1-y2+1) from these, so y is inverted.
  (set! graphics-device-coordinate-limits
        (lambda (d)
          (if (mitk:device? d)
              (values 0 (- mitk:height 1) (- mitk:width 1) 0)
              (mitk:orig-graphics-device-coordinate-limits d))))

  (set! graphics-disable-buffering
        (lambda (d) (if (mitk:device? d) 'done (mitk:orig-graphics-disable-buffering d))))
  (set! graphics-enable-buffering
        (lambda (d) (if (mitk:device? d) 'done (mitk:orig-graphics-enable-buffering d))))

  (set! graphics-bind-line-style
        (lambda (d style thunk)
          (if (mitk:device? d) (thunk) (mitk:orig-graphics-bind-line-style d style thunk))))
  (set! graphics-bind-drawing-mode
        (lambda (d mode thunk)
          (if (mitk:device? d) (thunk) (mitk:orig-graphics-bind-drawing-mode d mode thunk))))

  (set! graphics-operation
        (lambda (d op . rest)
          (if (mitk:device? d) 'done (apply mitk:orig-graphics-operation d op rest))))
  (set! graphics-set-coordinate-limits
        (lambda (d . rest)
          (if (mitk:device? d)
              (begin (vector-set! d 1 (mitk:arg rest 0 (vector-ref d 1)))
                     (vector-set! d 2 (mitk:arg rest 1 (vector-ref d 2)))
                     (vector-set! d 3 (mitk:arg rest 2 (vector-ref d 3)))
                     (vector-set! d 4 (mitk:arg rest 3 (vector-ref d 4)))
                     'done)
              (apply mitk:orig-graphics-set-coordinate-limits d rest))))
  (set! graphics-set-clip-rectangle
        (lambda (d . rest)
          (if (mitk:device? d) 'done (apply mitk:orig-graphics-set-clip-rectangle d rest))))
  'inline-plotting-enabled)

(define (mitk:uninstall!)
  (set! make-display-frame mitk:orig-make-display-frame)
  (set! frame mitk:orig-make-display-frame)
  (set! plot-frame mitk:orig-make-display-frame)
  (set! graphics-draw-point mitk:orig-graphics-draw-point)
  (set! graphics-draw-line mitk:orig-graphics-draw-line)
  (set! graphics-draw-text mitk:orig-graphics-draw-text)
  (set! graphics-clear mitk:orig-graphics-clear)
  (set! graphics-close mitk:orig-graphics-close)
  (set! graphics-flush mitk:orig-graphics-flush)
  (set! graphics-device? mitk:orig-graphics-device?)
  (set! graphics-coordinate-limits mitk:orig-graphics-coordinate-limits)
  (set! graphics-device-coordinate-limits mitk:orig-graphics-device-coordinate-limits)
  (set! graphics-disable-buffering mitk:orig-graphics-disable-buffering)
  (set! graphics-enable-buffering mitk:orig-graphics-enable-buffering)
  (set! graphics-bind-line-style mitk:orig-graphics-bind-line-style)
  (set! graphics-bind-drawing-mode mitk:orig-graphics-bind-drawing-mode)
  (set! graphics-operation mitk:orig-graphics-operation)
  (set! graphics-set-coordinate-limits mitk:orig-graphics-set-coordinate-limits)
  (set! graphics-set-clip-rectangle mitk:orig-graphics-set-clip-rectangle)
  'inline-plotting-disabled)

;;; -------------------------------------------------------------------- emit

;;; A line-oriented format, because MIT Scheme prints flonums as ".5" and "1.",
;;; which are not valid JSON but are perfectly good input to Python's float().
;;;
;;;   FRAME xmin xmax ymin ymax
;;;   POINTS x y x y ...
;;;   LINE x0 y0 x1 y1
;;;   TEXT x y the rest of the line
;;;
;;; Consecutive points are batched onto one POINTS line; a Poincare section is
;;; tens of thousands of them and one line each is a lot of pipe traffic.

(define (mitk:emit-ops ops)
  (let loop ((ops ops))
    (cond
     ((null? ops) 'done)
     ((eq? (car (car ops)) 'point)
      (display "POINTS")
      (let inner ((l ops))
        (if (and (pair? l) (eq? (car (car l)) 'point))
            (begin (display " ") (display (cadr (car l)))
                   (display " ") (display (caddr (car l)))
                   (inner (cdr l)))
            (begin (newline) (loop l)))))
     ((eq? (car (car ops)) 'line)
      (let ((op (car ops)))
        (display "LINE ") (display (cadr op)) (display " ") (display (caddr op))
        (display " ") (display (cadddr op)) (display " ")
        (display (list-ref op 4)) (newline))
      (loop (cdr ops)))
     ((eq? (car (car ops)) 'text)
      (let ((op (car ops)))
        (display "TEXT ") (display (cadr op)) (display " ") (display (caddr op))
        (display " ") (display (cadddr op)) (newline))
      (loop (cdr ops)))
     (else (loop (cdr ops))))))

(define (mitk:emit-device d)
  (display "FRAME ")
  (display (vector-ref d 1)) (display " ") (display (vector-ref d 2))
  (display " ") (display (vector-ref d 3)) (display " ") (display (vector-ref d 4))
  (newline)
  (mitk:emit-ops (reverse (mitk:ops d))))

;;; Emit every device drawn on since the last call, oldest first.
(define (mitk:emit-plots)
  (display "\nMITKPLOT<<\n")
  (for-each mitk:emit-device (reverse mitk:dirty))
  (display ">>MITKPLOT\n")
  (set! mitk:dirty '())
  'done)

;;; Forget everything drawn so far.
(define (mitk:reset-plots)
  (set! mitk:devices '())
  (set! mitk:dirty '())
  'done)

(mitk:install!)
