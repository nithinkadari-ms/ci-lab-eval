//! Reads `id<TAB>omml` lines on stdin and writes `id<TAB>ok|err<TAB>micros<TAB>latex-or-error` lines on
//! stdout (newlines, tabs and carriage returns in the output replaced by spaces) using easydoc-math 0.1.2.
use std::io::{self, BufRead, Write};
use std::time::Instant;

fn esc(s: &str) -> String {
    s.replace(['\n', '\t', '\r'], " ")
}

fn main() {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();
    for line in stdin.lock().lines() {
        let line = line.expect("stdin");
        let Some((id, omml)) = line.split_once('\t') else {
            continue;
        };
        let t = Instant::now();
        let res = easydoc_math::omml_to_latex::convert(omml);
        let us = t.elapsed().as_micros();
        match res {
            Ok(tex) => writeln!(out, "{}\tok\t{}\t{}", id, us, esc(&tex)).expect("stdout"),
            Err(e) => {
                let msg = format!("{e:?}");
                writeln!(out, "{}\terr\t{}\t{}", id, us, esc(&msg)).expect("stdout")
            }
        }
    }
}
