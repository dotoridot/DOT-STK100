fn main() {
    let mut args = vec!["validate".to_string()];
    args.extend(std::env::args().skip(1));
    std::process::exit(dot_stk100::run(args));
}
