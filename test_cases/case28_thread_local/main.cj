// case28: 线程局部变量测试（无竞争）
// 测试线程局部变量不应产生数据竞争

main() {
    // 每个线程有自己的局部变量
    spawn {
        let local1: Int64 = 1  // 局部变量
        local1 = local1 + 1    // 无竞争
    }
    
    spawn {
        let local2: Int64 = 2  // 局部变量
        local2 = local2 + 1    // 无竞争
    }
}