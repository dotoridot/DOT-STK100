fn main() {
    std::process::exit(dot_stk100::run(std::env::args().skip(1).collect()));
}
