// 测试用例10: synchronized块保护
// 使用synchronized块保护共享变量，无竞争

main() {
    var counter: Int64 = 0
    let lock = Object()
    
    // 线程1: synchronized保护
    spawn {
        synchronized(lock) {
            counter = counter + 1  // 写操作，受保护
        }
    }
    
    // 线程2: synchronized保护
    spawn {
        synchronized(lock) {
            counter = counter + 1  // 写操作，受保护
        }
    }
    
    println(counter)
}