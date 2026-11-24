//! Prints the Markdown anydoc 0.2.5 makes of each DOCX given on the command line.
fn main() {
    for path in std::env::args().skip(1) {
        match anydoc::to_markdown(&path) {
            Ok(md) => println!("{md}"),
            Err(e) => {
                eprintln!("{path}: {e}");
                std::process::exit(1);
            }
        }
    }
}
