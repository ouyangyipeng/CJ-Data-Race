// case37: join同步测试
// 测试使用join等待线程完成的场景

main() {
    var result: Int64 = 0
    
    let t1 = spawn {
        result = 100  // 写操作
    }
    
    let t2 = spawn {
        result = 200  // 写操作
    }
    
    // join等待线程完成
    t1.join()
    t2.join()
    
    // join后访问是安全的
    let final = result  // 读操作
}