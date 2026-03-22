// 测试用例5: 无竞争 - 线程独立变量
// 每个线程访问自己的局部变量

main() {
    // 线程1
    spawn {
        var local1: Int64 = 0
        local1 = local1 + 1  // 线程局部变量，无竞争
    }
    
    // 线程2
    spawn {
        var local2: Int64 = 0
        local2 = local2 + 1  // 线程局部变量，无竞争
    }
}