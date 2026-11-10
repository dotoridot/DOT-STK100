fn main() {
    let mut args = vec!["render".to_string()];
    args.extend(std::env::args().skip(1));
    std::process::exit(dot_stk100::run(args));
}
